from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from common.auth import get_current_admin, hash_password, validate_password
from common.exception_handler import CustomException
from common.pagination import clamp_page
from common.result import Result, PageInfo
from models import Admin

router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])


class AdminPublic(BaseModel):
    """对外输出视图，永远不暴露 password"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None


class AdminAdminView(AdminPublic):
    """管理员后台查看视图（当前字段与 AdminPublic 一致，独立声明便于后续扩展）"""
    pass


class AdminCreate(BaseModel):
    """新建管理员输入"""
    username: str
    password: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None


class AdminUpdate(BaseModel):
    """更新管理员输入，id 必填"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None


@router.post("/add")
async def add(data: AdminCreate):
    if await Admin.get_or_none(username=data.username) is not None:
        raise CustomException("账号重复")
    name = data.name if data.name is not None else data.username
    password = data.password if data.password is not None else "admin"
    validate_password(password)
    await Admin.create(
        username=data.username,
        password=hash_password(password),
        name=name,
        avatar=data.avatar,
        role='管理员',
        must_change_password=True,
    )
    return Result.success()


@router.put("/update")
async def update(data: AdminUpdate):
    update_data = data.model_dump(exclude_unset=True, exclude={'id'})
    if 'password' in update_data:
        validate_password(update_data['password'])
        update_data['password'] = hash_password(update_data['password'])
        # 管理员重置他人密码时，令其下次登录强制改密
        update_data['must_change_password'] = True
    await Admin.filter(id=data.id).update(**update_data)
    return Result.success()


@router.delete("/delete/{admin_id}")
async def delete(admin_id: int):
    await Admin.filter(id=admin_id).delete()
    return Result.success()


@router.delete("/deleteBatch")
async def delete_batch(ids: List[int]):
    await Admin.filter(id__in=ids).delete()
    return Result.success()


@router.put("/reset-password/{admin_id}")
async def reset_password(admin_id: int, data: AdminCreate):
    """管理员将指定账号的密码重置为指定值，并令其下次登录强制改密。"""
    admin = await Admin.get_or_none(id=admin_id)
    if admin is None:
        raise CustomException("管理员不存在")
    if not data.password:
        raise CustomException("请提供新密码")
    await Admin.filter(id=admin_id).update(
        password=hash_password(data.password),
        must_change_password=True,
    )
    return Result.success()


@router.get("/selectById/{admin_id}")
async def select_one(admin_id: int):
    admin = await Admin.get_or_none(id=admin_id)
    if admin is None:
        raise CustomException("管理员不存在")
    return Result.success(AdminAdminView.model_validate(admin).model_dump())


@router.get("/selectAll")
async def select_all(name: str = ""):
    admin_list = await Admin.filter(name__contains=name)
    admin_list = [AdminAdminView.model_validate(a).model_dump() for a in admin_list]
    return Result.success(admin_list)


@router.get("/selectPage")
async def select_page(name: str = "", pageNum: int = 1, pageSize: int = 10):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = Admin.filter(name__contains=name)
    admin_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    admin_list = [AdminAdminView.model_validate(a).model_dump() for a in admin_list]
    total = await query.count()
    pageinfo = PageInfo(total=total, list=admin_list)
    return Result.success(pageinfo)
