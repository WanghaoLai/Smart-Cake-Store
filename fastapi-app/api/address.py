from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction

from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Address, City, Province, Town

router = APIRouter(prefix="/address", dependencies=[Depends(get_current_user)])

# 创建 pydantic 只读模型 把数据库模型转化成pydantic模型
AddressPydantic = pydantic_model_creator(Address)
# 自动生成所有字段为 Optional 的更新模型
# 注意：is_default 已经由循环包含，此处显式重新定义只为加 alias。
# 必须在循环里 exclude 它，否则 create_model 会因重名 keyword 报错。
AddressCreatePydantic = create_model(
    "AddressPydantic",
    **{
        name: (Optional[field.annotation], None)
        for name, field in AddressPydantic.model_fields.items()
        if name not in {"province", "city", "town", "is_default"}
    },
    user_id=(Optional[int], Field(None, alias="userId")),
    province_id=(Optional[int], Field(None, alias="provinceId")),
    city_id=(Optional[int], Field(None, alias="cityId")),
    town_id=(Optional[int], Field(None, alias="townId")),
    is_default=(Optional[bool], Field(default=False, alias="isDefault")),
)


async def _resolve_region_names(payload: dict) -> None:
    """根据传入的 ID 反查省/市/区名称并写回 payload；ID 缺失则清空对应名称。
    调用方在 update 时需要把缺失的 ID 显式传 None 才会清空旧值。"""
    province_id = payload.get("province_id")
    if province_id:
        province = await Province.get_or_none(id=province_id)
        if province is None:
            raise CustomException("所选省份不存在")
        payload["province_name"] = province.name
    elif "province_id" in payload:
        payload["province_name"] = None

    city_id = payload.get("city_id")
    if city_id:
        city = await City.get_or_none(id=city_id)
        if city is None:
            raise CustomException("所选城市不存在")
        payload["city_name"] = city.name
    elif "city_id" in payload:
        payload["city_name"] = None

    town_id = payload.get("town_id")
    if town_id:
        town = await Town.get_or_none(id=town_id)
        if town is None:
            raise CustomException("所选区县不存在")
        payload["town_name"] = town.name
    elif "town_id" in payload:
        payload["town_name"] = None


def _compose_full_address(payload: dict) -> Optional[str]:
    """省+市+区+详细地址 拼接为单一字符串。全部为空时返回 None。"""
    parts = [
        payload.get("province_name"),
        payload.get("city_name"),
        payload.get("town_name"),
        payload.get("detail"),
    ]
    parts = [p for p in parts if p]
    return "".join(parts) if parts else None


def _strip_relation_keys(payload: dict) -> dict:
    """Tortoise 不允许通过关系字段名（province/city/town）直接 update，
    必须用 <field>__id 形式。这里把残留的关系键清掉。"""
    for key in ("province", "city", "town"):
        payload.pop(key, None)
    return payload


def _to_camel_case(snake: str) -> str:
    """snake_case → camelCase（前端约定）。
    AddressPydantic 默认输出 snake_case（如 province_name, is_default），
    但前端模板用 camelCase（provinceName, isDefault）——必须转换。"""
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _address_to_dict(address) -> dict:
    """ORM 实例 → camelCase dict。
    所有面向前端的 address 列表/单条返回都必须经过此函数。

    Tortoise 的 pydantic_model_creator 输出关系字段（如 province/city/town/user）
    是嵌套对象，不是 ID。前端编辑回显需要 provinceId 等 ID 字段，所以从 ORM
    实例单独取 _id 列；同时清掉关系对象和反向关系（orderss），避免冗余传输。
    """
    raw = AddressPydantic.model_validate(address).model_dump()
    camel = {_to_camel_case(k): v for k, v in raw.items()}
    # 补全外键 ID（前端编辑回显 + 下单页 find default 都依赖）
    camel["userId"] = address.user_id
    camel["provinceId"] = address.province_id
    camel["cityId"] = address.city_id
    camel["townId"] = address.town_id
    # 删掉关系对象和反向关系（user/province/city/town/orderss）——前端不需要
    for k in ("user", "province", "city", "town", "orderss"):
        camel.pop(k, None)
    return camel


async def _enforce_default_uniqueness(user_id: int, exclude_id: Optional[int] = None) -> None:
    """同一用户最多 1 条默认地址。设默认前把该用户其他 is_default=True 的地址置 false。
    必须在事务内调用以保证原子性。"""
    query = Address.filter(user_id=user_id, is_default=True)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    await query.update(is_default=False)


async def _maybe_promote_default(user_id: int) -> None:
    """删除默认地址后兜底：把该用户最早的一条地址提升为默认。
    避免用户没默认地址导致下单页找不到默认选项。"""
    has_default = await Address.filter(user_id=user_id, is_default=True).exists()
    if has_default:
        return
    candidate = await Address.filter(user_id=user_id).order_by("id").first()
    if candidate is not None:
        # update_fields 限制只更新 is_default，避免触发 auto_now 时间戳
        candidate.is_default = True
        await candidate.save(update_fields=["is_default"])


@router.post("/add")
async def add(address_pydantic: AddressCreatePydantic, current_user: dict = Depends(get_current_user)):
    create_data = address_pydantic.model_dump(exclude_unset=True, exclude={'id', 'user_id'})
    await _resolve_region_names(create_data)
    create_data = _strip_relation_keys(create_data)
    create_data["address"] = _compose_full_address(create_data)
    create_data['user_id'] = current_user["user_id"]

    # 用户首条地址自动设为默认；显式 is_default=True 时清掉其他默认
    user_address_count = await Address.filter(user_id=current_user["user_id"]).count()
    is_default_requested = bool(create_data.get("is_default"))
    if user_address_count == 0 or is_default_requested:
        create_data["is_default"] = True
    else:
        create_data["is_default"] = False

    async with in_transaction():
        if create_data["is_default"]:
            await _enforce_default_uniqueness(current_user["user_id"])
        await Address.create(**create_data)
    return Result.success()


@router.put("/update")
async def update(address_pydantic: AddressCreatePydantic, current_user: dict = Depends(get_current_user)):
    if address_pydantic.id is None:
        raise CustomException("地址ID不能为空")
    target = await Address.get_or_none(id=address_pydantic.id)
    if target is None:
        raise CustomException("地址不存在")
    if current_user["role"] != "管理员" and target.user_id != current_user["user_id"]:
        raise CustomException("无权操作该地址")
    update_data = address_pydantic.model_dump(exclude_unset=True, exclude={'id', 'user_id'})
    await _resolve_region_names(update_data)
    update_data = _strip_relation_keys(update_data)
    # 用户改了任何结构化字段就重新拼接 address；否则保留旧值
    region_keys = {"province_id", "province_name", "city_id", "city_name",
                   "town_id", "town_name", "detail"}
    if region_keys & update_data.keys():
        merged = {**AddressPydantic.model_validate(target).model_dump(),
                  **update_data}
        composed = _compose_full_address(merged)
        if composed is not None:
            update_data["address"] = composed
        elif "address" in update_data:
            # 全部清空：允许把拼接字段写为 NULL
            update_data["address"] = None

    # 默认地址互斥更新：要把这条设为默认，必须先把同 user 的其他默认清掉
    if update_data.get("is_default"):
        async with in_transaction():
            await _enforce_default_uniqueness(
                target.user_id, exclude_id=target.id
            )
            await Address.filter(id=address_pydantic.id).update(**update_data)
    else:
        await Address.filter(id=address_pydantic.id).update(**update_data)
    return Result.success()


@router.put("/set_default/{address_id}")
async def set_default(address_id: int, current_user: dict = Depends(get_current_user)):
    """把指定地址设为当前用户的默认地址。其他地址同步置 false（事务内）。"""
    target = await Address.get_or_none(id=address_id)
    if target is None:
        raise CustomException("地址不存在")
    if current_user["role"] != "管理员" and target.user_id != current_user["user_id"]:
        raise CustomException("无权操作该地址")
    async with in_transaction():
        await _enforce_default_uniqueness(target.user_id, exclude_id=address_id)
        await Address.filter(id=address_id).update(is_default=True)
    return Result.success()


@router.delete("/delete/{address_id}")
async def delete(address_id: int, current_user: dict = Depends(get_current_user)):
    target = await Address.get_or_none(id=address_id)
    if target is None:
        raise CustomException("地址不存在")
    if current_user["role"] != "管理员" and target.user_id != current_user["user_id"]:
        raise CustomException("无权操作该地址")
    user_id = target.user_id
    was_default = target.is_default
    await Address.filter(id=address_id).delete()
    # 删除的是默认地址：自动把同 user 最早的一条提升为默认
    if was_default:
        await _maybe_promote_default(user_id)
    return Result.success()


# 查询所有
@router.get("/selectAll")
async def select_all(userId: int, current_user: dict = Depends(get_current_user)):
    # 普通用户只能查询自己的地址
    if current_user["role"] != "管理员":
        userId = current_user["user_id"]
    address_list = await Address.filter(user_id=userId) # 模糊查询
    return Result.success([_address_to_dict(a) for a in address_list])


@router.get("/selectPage")
async def select(address: str = "", userId: int = 0,  pageNum: int = 1, pageSize: int = 5,
                 current_user: dict = Depends(get_current_user)):
    # 普通用户强制仅能查自己的地址
    if current_user["role"] != "管理员":
        userId = current_user["user_id"]
    # 同时获取分页数据和总数；新结构化字段已包含在 AddressPydantic 里
    query = Address.filter(address__contains=address).prefetch_related('user')
    if userId > 0:
        query = query.filter(user_id=userId) # 过滤掉不属于自己的address
    # 获取分页数据
    address_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    address_list = [
        {
            **_address_to_dict(address),
            "userName": address.user.name if address.user else None,
        }
        for address in address_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=address_list)
    return Result.success(pageinfo)


