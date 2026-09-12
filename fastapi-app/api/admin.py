import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from tortoise.exceptions import IntegrityError
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from common.audit import client_ip, record_audit_required
from common.auth import async_hash_password, get_current_admin, validate_password
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
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=255)
    password: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("账号不能为空")
        return value


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1)


class AdminUpdate(BaseModel):
    """更新管理员输入，id 必填"""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    username: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None

    @field_validator("username", "password", mode="before")
    @classmethod
    def reject_null_credentials(cls, value):
        if value is None:
            raise ValueError("账号和密码不能为 null")
        return value

    @field_validator("username")
    @classmethod
    def normalize_update_username(cls, value: str | None):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("账号不能为空")
        return value


@router.post("/add")
async def add(data: AdminCreate, current_user: dict = Depends(get_current_admin), request: Request = None):
    if await Admin.get_or_none(username=data.username) is not None:
        raise CustomException("账号重复")
    name = data.name if data.name is not None else data.username
    generated_password = data.password is None
    password = data.password if data.password is not None else secrets.token_urlsafe(12)
    validate_password(password)
    password_hash = await async_hash_password(password)
    try:
        async with in_transaction() as connection:
            created = await Admin.create(
                username=data.username,
                password=password_hash,
                name=name,
                avatar=data.avatar,
                role='管理员',
                must_change_password=True,
                using_db=connection,
            )
            await record_audit_required(
                current_user, "admin.create", "admin", created.id,
                detail={"username": data.username, "password_generated": generated_password},
                ip=client_ip(request), using_db=connection,
            )
    except IntegrityError as exc:
        raise CustomException("账号重复") from exc
    return Result.success({"initial_password": password} if generated_password else None)


@router.put("/update")
async def update(data: AdminUpdate, current_user: dict = Depends(get_current_admin), request: Request = None):
    update_data = data.model_dump(exclude_unset=True, exclude={'id'})
    password_changed = 'password' in update_data
    if password_changed:
        validate_password(update_data['password'])
        update_data['password'] = await async_hash_password(update_data['password'])
        update_data['must_change_password'] = True
    try:
        async with in_transaction() as connection:
            target = await Admin.filter(id=data.id).using_db(connection).select_for_update().first()
            if target is None:
                raise CustomException("管理员不存在")
            if password_changed:
                update_data['token_version'] = F("token_version") + 1
            await Admin.filter(id=data.id).using_db(connection).update(**update_data)
            await record_audit_required(
                current_user, "admin.update", "admin", data.id,
                detail={"fields": sorted(update_data.keys()), "password_changed": password_changed},
                ip=client_ip(request), using_db=connection,
            )
    except IntegrityError as exc:
        raise CustomException("账号重复") from exc
    return Result.success()


@router.delete("/delete/{admin_id}")
async def delete(admin_id: int, current_user: dict = Depends(get_current_admin), request: Request = None):
    async with in_transaction() as connection:
        target = await Admin.filter(id=admin_id).using_db(connection).select_for_update().first()
        await Admin.filter(id=admin_id).using_db(connection).delete()
        await record_audit_required(
            current_user, "admin.delete", "admin", admin_id,
            detail={"username": target.username if target else None},
            ip=client_ip(request), using_db=connection,
        )
    return Result.success()


@router.delete("/deleteBatch")
async def delete_batch(ids: List[int], current_user: dict = Depends(get_current_admin), request: Request = None):
    async with in_transaction() as connection:
        targets = await Admin.filter(id__in=ids).using_db(connection).select_for_update()
        await Admin.filter(id__in=ids).using_db(connection).delete()
        await record_audit_required(
            current_user, "admin.delete_batch", "admin", None,
            detail={"ids": ids, "usernames": [a.username for a in targets]},
            ip=client_ip(request), using_db=connection,
        )
    return Result.success()


@router.put("/reset-password/{admin_id}")
async def reset_password(admin_id: int, data: PasswordResetRequest, current_user: dict = Depends(get_current_admin), request: Request = None):
    """管理员将指定账号的密码重置为指定值，并令其下次登录强制改密。"""
    validate_password(data.password)
    password_hash = await async_hash_password(data.password)
    async with in_transaction() as connection:
        admin = await Admin.filter(id=admin_id).using_db(connection).select_for_update().first()
        if admin is None:
            raise CustomException("管理员不存在")
        await Admin.filter(id=admin_id).using_db(connection).update(
            password=password_hash,
            must_change_password=True,
            token_version=F("token_version") + 1,
        )
        await record_audit_required(
            current_user, "admin.reset_password", "admin", admin_id,
            detail={"username": admin.username, "forced_change": True},
            ip=client_ip(request), using_db=connection,
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
