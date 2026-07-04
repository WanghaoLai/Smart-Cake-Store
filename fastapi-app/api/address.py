from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator

from common.auth import get_current_user
from common.result import Result, PageInfo
from models import Address

router = APIRouter(prefix="/address", dependencies=[Depends(get_current_user)])

# 创建 pydantic 只读模型 把数据库模型转化成pydantic模型
AddressPydantic = pydantic_model_creator(Address)
# 自动生成所有字段为 Optional 的更新模型
AddressCreatePydantic = create_model(
    "AddressPydantic",
    **{
        # 从只读模型中读取所有字段然后给它设置成可选
        name: (Optional[field.annotation], None)
        for name, field in AddressPydantic.model_fields.items()
    },
    user_id=(Optional[int], Field(None, alias="userId"))
)

@router.post("/add")
async def add(address_pydantic: AddressCreatePydantic):
    create_data = address_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await Address.create(**create_data)
    return Result.success()


@router.put("/update")
async def update(address_pydantic: AddressCreatePydantic):
    update_data = address_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await Address.filter(id=address_pydantic.id).update(**update_data)
    return Result.success()


@router.delete("/delete/{address_id}")
async def delete(address_id: int):
    await Address.filter(id=address_id).delete()
    return Result.success()


# 查询所有
@router.get("/selectAll")
async def select_all(userId: int):
    address_list = await Address.filter(user_id=userId) # 模糊查询
    return Result.success(address_list)


@router.get("/selectPage")
async def select(address: str = "", userId: int = 0,  pageNum: int = 1, pageSize: int = 5):
    # 同时获取分页数据和总数
    query = Address.filter(address__contains=address).prefetch_related('user')
    if userId > 0:
        query = query.filter(user_id=userId) # 过滤掉不属于自己的address
    # 获取分页数据
    address_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    address_list = [
        {
            **AddressPydantic.model_validate(address).model_dump(),  # id=xxx,no=xxx,name=xxx
            "userName": address.user.name if address.user else None,
        }
        for address in address_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=address_list)
    return Result.success(pageinfo)

