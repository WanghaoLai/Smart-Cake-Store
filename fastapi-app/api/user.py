from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model
from tortoise.contrib.pydantic import pydantic_model_creator

from common.auth import get_current_user, hash_password
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import User

router = APIRouter(prefix="/user", dependencies=[Depends(get_current_user)])
UserPydantic = pydantic_model_creator(User)
UserCreatePydantic = create_model(
    "UserPydantic",
    **{
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
    create_data['password'] = hash_password(create_data['password'])
    create_data['role'] = '用户'
    await User.create(**create_data)
    return Result.success()


@router.put("/update")
async def update(user_pydantic: UserCreatePydantic):
    update_data = user_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    if 'password' in update_data:
        update_data['password'] = hash_password(update_data['password'])
    await User.filter(id=user_pydantic.id).update(**update_data)
    return Result.success()


@router.delete("/delete/{user_id}")
async def delete(user_id: int):
    await User.filter(id=user_id).delete()
    return Result.success()


@router.get("/selectPage")
async def select(name: str = "", pageNum: int = 1, pageSize: int = 5):
    query = User.filter(name__contains=name)
    user_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    user_list = [
        UserPydantic.model_validate(user).model_dump()
        for user in user_list
    ]
    total = await query.count()
    pageinfo = PageInfo(total=total, list=user_list)
    return Result.success(pageinfo)
