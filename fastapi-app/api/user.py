from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from common.auth import get_current_admin, hash_password, validate_password
from common.exception_handler import CustomException
from common.pagination import clamp_page
from common.result import Result, PageInfo
from models import User

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
    """管理员后台查看视图（当前字段与 UserPublic 一致，独立声明便于后续扩展）"""
    pass


class UserCreate(BaseModel):
    """新建用户输入"""
    username: str
    password: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None


class UserUpdate(BaseModel):
    """更新用户输入，id 必填"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None


@router.post("/add")
async def add(data: UserCreate):
    if await User.get_or_none(username=data.username) is not None:
        raise CustomException("账号重复")
    name = data.name if data.name is not None else data.username
    password = data.password if data.password is not None else "123"
    validate_password(password)
    await User.create(
        username=data.username,
        password=hash_password(password),
        name=name,
        avatar=data.avatar,
        role='用户',
        must_change_password=True,
    )
    return Result.success()


@router.put("/update")
async def update(data: UserUpdate):
    update_data = data.model_dump(exclude_unset=True, exclude={'id'})
    if 'password' in update_data:
        validate_password(update_data['password'])
        update_data['password'] = hash_password(update_data['password'])
        # 管理员重置他人密码时，令其下次登录强制改密
        update_data['must_change_password'] = True
    await User.filter(id=data.id).update(**update_data)
    return Result.success()


@router.put("/reset-password/{user_id}")
async def reset_password(user_id: int, data: UserCreate):
    """管理员将指定用户密码重置为指定值，并令其下次登录强制改密。"""
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise CustomException("用户不存在")
    if not data.password:
        raise CustomException("请提供新密码")
    validate_password(data.password)
    await User.filter(id=user_id).update(
        password=hash_password(data.password),
        must_change_password=True,
    )
    return Result.success()


@router.delete("/delete/{user_id}")
async def delete(user_id: int):
    await User.filter(id=user_id).delete()
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
