from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import create_model
from tortoise.contrib.pydantic import pydantic_model_creator

from common.auth import get_current_user, hash_password
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Admin

router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_user)])
AdminPydantic = pydantic_model_creator(Admin)
AdminCreatePydantic = create_model(
    "AdminPydantic",
    **{
        name: (Optional[field.annotation], None)
        for name, field in AdminPydantic.model_fields.items()
    }
)


@router.post("/add")
async def add(admin_create_pydantic: AdminCreatePydantic):
    admin = await Admin.get_or_none(username=admin_create_pydantic.username)
    if admin is not None:
        raise CustomException("账号重复")
    if admin_create_pydantic.name is None:
        admin_create_pydantic.name = admin_create_pydantic.username
    if admin_create_pydantic.password is None:
        admin_create_pydantic.password = "admin"
    create_data = admin_create_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    create_data['password'] = hash_password(create_data['password'])
    create_data['role'] = '管理员'
    await Admin.create(**create_data)
    return Result.success()


@router.put("/update")
async def update(admin_create_pydantic: AdminCreatePydantic):
    update_data = admin_create_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    if 'password' in update_data:
        update_data['password'] = hash_password(update_data['password'])
    await Admin.filter(id=admin_create_pydantic.id).update(**update_data)
    return Result.success()


@router.delete("/delete/{admin_id}")
async def delete(admin_id: int):
    await Admin.filter(id=admin_id).delete()
    return Result.success()


@router.delete("/deleteBatch")
async def delete_batch(ids: List[int]):
    await Admin.filter(id__in=ids).delete()
    return Result.success()


@router.get("/selectById/{admin_id}")
async def select_one(admin_id: int):
    admin = await Admin.get(id=admin_id)
    return Result.success(admin)


@router.get("/selectAll")
async def select_all(name: str = ""):
    admin_list = await Admin.filter(name__contains=name)
    return Result.success(admin_list)


@router.get("/selectPage")
async def select_page(name: str = "", pageNum: int = 1, pageSize: int = 10):
    query = Admin.filter(name__contains=name)
    admin_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    admin_list = [
        AdminPydantic.model_validate(admin).model_dump()
        for admin in admin_list
    ]
    total = await query.count()
    pageinfo = PageInfo(total=total, list=admin_list)
    return Result.success(pageinfo)
