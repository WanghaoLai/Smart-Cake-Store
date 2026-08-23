import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from common.audit import client_ip, record_audit
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
async def add(data: AdminCreate, current_user: dict = Depends(get_current_admin), request: Request = None):
    if await Admin.get_or_none(username=data.username) is not None:
        raise CustomException("账号重复")
    name = data.name if data.name is not None else data.username
    generated_password = data.password is None
    password = data.password if data.password is not None else secrets.token_urlsafe(12)
    validate_password(password)
    await Admin.create(
        username=data.username,
        password=hash_password(password),
        name=name,
        avatar=data.avatar,
        role='管理员',
        must_change_password=True,
    )
    created = await Admin.get(username=data.username)
    await record_audit(
        current_user, "admin.create", "admin", created.id,
        detail={"username": data.username, "password_generated": generated_password},
        ip=client_ip(request),
    )
    return Result.success({"initial_password": password} if generated_password else None)


@router.put("/update")
async def update(data: AdminUpdate, current_user: dict = Depends(get_current_admin), request: Request = None):
    update_data = data.model_dump(exclude_unset=True, exclude={'id'})
    if 'password' in update_data:
        validate_password(update_data['password'])
        update_data['password'] = hash_password(update_data['password'])
        # 管理员重置他人密码时，令其下次登录强制改密
        update_data['must_change_password'] = True
        target = await Admin.get_or_none(id=data.id)
        if target is None:
            raise CustomException("管理员不存在")
        update_data['token_version'] = int(target.token_version) + 1
    await Admin.filter(id=data.id).update(**update_data)
    await record_audit(
        current_user, "admin.update", "admin", data.id,
        detail={"fields": sorted(update_data.keys()), "password_changed": "password" in update_data},
        ip=client_ip(request),
    )
    return Result.success()


@router.delete("/delete/{admin_id}")
async def delete(admin_id: int, current_user: dict = Depends(get_current_admin), request: Request = None):
    target = await Admin.get_or_none(id=admin_id)
    await Admin.filter(id=admin_id).delete()
    await record_audit(
        current_user, "admin.delete", "admin", admin_id,
        detail={"username": target.username if target else None},
        ip=client_ip(request),
    )
    return Result.success()


@router.delete("/deleteBatch")
async def delete_batch(ids: List[int], current_user: dict = Depends(get_current_admin), request: Request = None):
    targets = await Admin.filter(id__in=ids)
    await Admin.filter(id__in=ids).delete()
    await record_audit(
        current_user, "admin.delete_batch", "admin", None,
        detail={"ids": ids, "usernames": [a.username for a in targets]},
        ip=client_ip(request),
    )
    return Result.success()


@router.put("/reset-password/{admin_id}")
async def reset_password(admin_id: int, data: AdminCreate, current_user: dict = Depends(get_current_admin), request: Request = None):
    """管理员将指定账号的密码重置为指定值，并令其下次登录强制改密。"""
    admin = await Admin.get_or_none(id=admin_id)
    if admin is None:
        raise CustomException("管理员不存在")
    if not data.password:
        raise CustomException("请提供新密码")
    validate_password(data.password)
    await Admin.filter(id=admin_id).update(
        password=hash_password(data.password),
        must_change_password=True,
        token_version=int(admin.token_version) + 1,
    )
    await record_audit(
        current_user, "admin.reset_password", "admin", admin_id,
        detail={"username": admin.username, "forced_change": True},
        ip=client_ip(request),
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
