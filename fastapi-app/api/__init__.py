import importlib
import pkgutil

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from common.auth import hash_password, verify_password, create_access_token, get_current_user
from common.exception_handler import CustomException
from common.result import Result
from models import Admin, User


class Account(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = None
    username: str = None
    password: str = None
    newPassword: str = None
    role: str = None
    name: str = None
    avatar: str = None


api_router = APIRouter()


# 登录
@api_router.post("/login")
async def login(account: Account):
    if account.role == '管理员':
        user = await Admin.get_or_none(username=account.username)
    else:
        user = await User.get_or_none(username=account.username)

    if user is None:
        raise CustomException("账号不存在，请注册账号")

    is_valid, needs_upgrade = verify_password(account.password, user.password)
    if not is_valid:
        raise CustomException("账号或密码错误")

    if needs_upgrade:
        hashed = hash_password(account.password)
        if account.role == '管理员':
            await Admin.filter(id=user.id).update(password=hashed)
        else:
            await User.filter(id=user.id).update(password=hashed)

    token = create_access_token({
        "id": user.id,
        "username": user.username,
        "role": account.role,
    })

    user_data = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "avatar": user.avatar,
        "role": account.role,
    }
    return Result.success({"token": token, "user": user_data})


# 注册
@api_router.post("/register")
async def register(account: Account):
    user = await User.get_or_none(username=account.username)
    if user is not None:
        raise CustomException("账号重复")
    if account.name is None:
        account.name = account.username
    if account.password is None:
        account.password = "123"
    create_data = account.model_dump(exclude_unset=True, exclude={'id'})
    create_data['password'] = hash_password(create_data['password'])
    create_data['role'] = '用户'
    await User.create(**create_data)
    return Result.success()


# 修改密码
@api_router.put("/updatePassword")
async def update_password(account: Account, current_user: dict = Depends(get_current_user)):
    if account.role == '管理员':
        admin = await Admin.get(id=account.id)
        if admin is None:
            raise CustomException("未找到用户")
        is_valid, _ = verify_password(account.password, admin.password)
        if not is_valid:
            raise CustomException("原密码错误")
        new_hashed = hash_password(account.newPassword)
        if verify_password(account.newPassword, admin.password)[0]:
            raise CustomException("新密码不能原密码跟相同")
        await Admin.filter(id=admin.id).update(password=new_hashed)
    if account.role == '用户':
        user = await User.get(id=account.id)
        if user is None:
            raise CustomException("未找到用户")
        is_valid, _ = verify_password(account.password, user.password)
        if not is_valid:
            raise CustomException("原密码错误")
        new_hashed = hash_password(account.newPassword)
        if verify_password(account.newPassword, user.password)[0]:
            raise CustomException("新密码不能原密码跟相同")
        await User.filter(id=user.id).update(password=new_hashed)
    return Result.success()


# 自动导入当前目录下的所有模块
for _, module_name, _ in pkgutil.iter_modules(__path__, __name__ + "."):
    module = importlib.import_module(module_name)
    if hasattr(module, "router"):
        api_router.include_router(module.router)
