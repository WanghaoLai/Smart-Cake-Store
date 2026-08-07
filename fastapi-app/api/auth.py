"""Authentication endpoints."""

from fastapi import APIRouter, Depends

from api.auth_schemas import LoginRequest, PasswordUpdateRequest, RegisterRequest
from common.auth import create_access_token, get_current_user, hash_password, verify_password
from common.exception_handler import CustomException
from common.result import Result
from models import Admin, User


router = APIRouter()


@router.post("/login")
async def login(account: LoginRequest):
    if account.role == "管理员":
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
        model = Admin if account.role == "管理员" else User
        await model.filter(id=user.id).update(password=hashed)

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
        "must_change_password": bool(getattr(user, "must_change_password", False)),
    }
    return Result.success({"token": token, "user": user_data})


@router.post("/register")
async def register(account: RegisterRequest):
    if await User.get_or_none(username=account.username) is not None:
        raise CustomException("账号重复")
    await User.create(
        username=account.username,
        password=hash_password(account.password),
        name=account.name or account.username,
        avatar=account.avatar,
        role="用户",
    )
    return Result.success()


@router.put("/updatePassword")
async def update_password(account: PasswordUpdateRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    role = current_user["role"]
    model = Admin if role == "管理员" else User
    user = await model.get_or_none(id=user_id)
    if user is None:
        raise CustomException("未找到用户")
    if not verify_password(account.password, user.password)[0]:
        raise CustomException("原密码错误")
    if verify_password(account.newPassword, user.password)[0]:
        raise CustomException("新密码不能原密码跟相同")
    await model.filter(id=user_id).update(
        password=hash_password(account.newPassword),
        must_change_password=False,
    )
    return Result.success()
