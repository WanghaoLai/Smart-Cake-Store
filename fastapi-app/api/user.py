from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model
from tortoise.contrib.pydantic import pydantic_model_creator

from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import User

router = APIRouter(prefix="/user")
# 创建 pydantic 只读模型 把数据库模型转化成pydantic模型
UserPydantic = pydantic_model_creator(User)
# 自动生成所有字段为 Optional 的更新模型
UserCreatePydantic = create_model(
    "UserPydantic",
    **{
        # 从只读模型中读取所有字段然后给它设置成可选
        name: (Optional[field.annotation], None)
        for name, field in UserPydantic.model_fields.items()
    }
)


@router.post("/add")
async def add(user_pydantic: UserCreatePydantic):
    user = await User.get_or_none(username=user_pydantic.username)
    if user is not None:
        raise CustomException("账号重复")
    if user_pydantic.name is None:
        user_pydantic.name = user_pydantic.username
    if user_pydantic.password is None:
        user_pydantic.password = "123"
    create_data = user_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    create_data['role'] = '用户'
    await User.create(**create_data)
    return Result.success()


@router.put("/update")
async def update(user_pydantic: UserCreatePydantic):
    update_data = user_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await User.filter(id=user_pydantic.id).update(**update_data)
    return Result.success()


@router.delete("/delete/{user_id}")
async def delete(user_id: int):
    await User.filter(id=user_id).delete()
    return Result.success()


@router.get("/selectPage")
async def select(name: str = "", pageNum: int = 1, pageSize: int = 5):
    # 同时获取分页数据和总数
    query = User.filter(name__contains=name)
    # 获取分页数据
    user_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    user_list = [
        # 遍历每个 User 实例（ORM实例），通过 Pydantic 模型，转为字典
        UserPydantic.model_validate(user).model_dump()
        for user in user_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=user_list)
    return Result.success(pageinfo)

