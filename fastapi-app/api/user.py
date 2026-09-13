import secrets
from decimal import Decimal
from typing import Optional

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
from models import Address, Favorite, Orders, Review, User, WalletTransaction

router = APIRouter(prefix="/user", dependencies=[Depends(get_current_admin)])


class UserPublic(BaseModel):
    """对外输出视图，永远不暴露 password"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None


class UserAdminView(UserPublic):
    """管理员可查看余额，但任何用户编辑接口都不能直接改余额。"""
    balance: Decimal = Decimal("0.00")


class UserCreate(BaseModel):
    """新建用户输入"""
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


class UserUpdate(BaseModel):
    """更新用户输入，id 必填"""
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
async def add(data: UserCreate, current_user: dict = Depends(get_current_admin), request: Request = None):
    if await User.get_or_none(username=data.username) is not None:
        raise CustomException("账号重复")
    name = data.name if data.name is not None else data.username
    generated_password = data.password is None
    password = data.password if data.password is not None else secrets.token_urlsafe(12)
    validate_password(password)
    password_hash = await async_hash_password(password)
    try:
        async with in_transaction() as connection:
            created = await User.create(
                username=data.username,
                password=password_hash,
                name=name,
                avatar=data.avatar,
                role='用户',
                must_change_password=True,
                using_db=connection,
            )
            await record_audit_required(
                current_user, "user.create", "user", created.id,
                detail={"username": data.username, "password_generated": generated_password},
                ip=client_ip(request), using_db=connection,
            )
    except IntegrityError as exc:
        raise CustomException("账号重复") from exc
    return Result.success({"initial_password": password} if generated_password else None)


@router.put("/update")
async def update(data: UserUpdate, current_user: dict = Depends(get_current_admin), request: Request = None):
    update_data = data.model_dump(exclude_unset=True, exclude={'id'})
    password_changed = 'password' in update_data
    if password_changed:
        validate_password(update_data['password'])
        update_data['password'] = await async_hash_password(update_data['password'])
        update_data['must_change_password'] = True
    try:
        async with in_transaction() as connection:
            target = await User.filter(id=data.id).using_db(connection).select_for_update().first()
            if target is None:
                raise CustomException("用户不存在")
            if password_changed:
                update_data['token_version'] = F("token_version") + 1
            await User.filter(id=data.id).using_db(connection).update(**update_data)
            await record_audit_required(
                current_user, "user.update", "user", data.id,
                detail={"fields": sorted(update_data.keys()), "password_changed": password_changed},
                ip=client_ip(request), using_db=connection,
            )
    except IntegrityError as exc:
        raise CustomException("账号重复") from exc
    return Result.success()


@router.put("/reset-password/{user_id}")
async def reset_password(user_id: int, data: PasswordResetRequest, current_user: dict = Depends(get_current_admin), request: Request = None):
    """管理员将指定用户密码重置为指定值，并令其下次登录强制改密。"""
    validate_password(data.password)
    password_hash = await async_hash_password(data.password)
    async with in_transaction() as connection:
        user = await User.filter(id=user_id).using_db(connection).select_for_update().first()
        if user is None:
            raise CustomException("用户不存在")
        await User.filter(id=user_id).using_db(connection).update(
            password=password_hash,
            must_change_password=True,
            token_version=F("token_version") + 1,
        )
        await record_audit_required(
            current_user, "user.reset_password", "user", user_id,
            detail={"username": user.username, "forced_change": True},
            ip=client_ip(request), using_db=connection,
        )
    return Result.success()


@router.delete("/delete/{user_id}")
async def delete(user_id: int, current_user: dict = Depends(get_current_admin), request: Request = None):
    async with in_transaction() as connection:
        target = await User.filter(id=user_id).using_db(connection).select_for_update().first()
        has_business_data = any((
            await Orders.filter(user_id=user_id).using_db(connection).exists(),
            await Review.filter(user_id=user_id).using_db(connection).exists(),
            await Address.filter(user_id=user_id).using_db(connection).exists(),
            await Favorite.filter(user_id=user_id).using_db(connection).exists(),
            await WalletTransaction.filter(user_id=user_id).using_db(connection).exists(),
        ))
        if has_business_data:
            raise CustomException("用户已有订单或关联数据，为保留审计记录不能物理删除")
        await User.filter(id=user_id).using_db(connection).delete()
        await record_audit_required(
            current_user, "user.delete", "user", user_id,
            detail={"username": target.username if target else None},
            ip=client_ip(request), using_db=connection,
        )
    return Result.success()


@router.get("/selectPage")
async def select(name: str = "", pageNum: int = 1, pageSize: int = 5):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = User.filter(name__contains=name)
    user_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    user_list = [UserAdminView.model_validate(u).model_dump() for u in user_list]
    total = await query.count()
    pageinfo = PageInfo(total=total, list=user_list)
    return Result.success(pageinfo)
