"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from tortoise.exceptions import IntegrityError

from api.auth_schemas import LoginRequest, PasswordUpdateRequest, RegisterRequest
from common.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    validate_password,
    verify_password,
)
from common.exception_handler import CustomException
from common.result import Result
from common.rate_limit import SlidingWindowRateLimiter
from models import Admin, User
from settings import (
    AUTH_RATE_WINDOW_SECONDS,
    LOGIN_RATE_LIMIT_PER_ACCOUNT,
    LOGIN_RATE_LIMIT_PER_IP,
    REGISTER_RATE_LIMIT_PER_IP,
)


router = APIRouter()

login_account_limiter = SlidingWindowRateLimiter(
    LOGIN_RATE_LIMIT_PER_ACCOUNT, AUTH_RATE_WINDOW_SECONDS,
)
login_ip_limiter = SlidingWindowRateLimiter(
    LOGIN_RATE_LIMIT_PER_IP, AUTH_RATE_WINDOW_SECONDS,
)
register_ip_limiter = SlidingWindowRateLimiter(
    REGISTER_RATE_LIMIT_PER_IP, AUTH_RATE_WINDOW_SECONDS,
)


def _client_ip(request: Request) -> str:
    # 不盲信 X-Forwarded-For：只有在反向代理层明确覆盖该头时才应使用。
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def login(account: LoginRequest, request: Request):
    ip = _client_ip(request)
    account_key = f"{ip}:{account.role}:{account.username.casefold()}"
    if not login_ip_limiter.allow(ip) or not login_account_limiter.allow(account_key):
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
    if account.role == "管理员":
        user = await Admin.get_or_none(username=account.username)
    else:
        user = await User.get_or_none(username=account.username)

    if user is None:
        # 不区分“账号不存在”与“密码错误”，避免用户名枚举。
        raise CustomException("账号或密码错误")

    is_valid, needs_upgrade = verify_password(account.password, user.password)
    if not is_valid:
        raise CustomException("账号或密码错误")

    # 账号维度只累计失败尝试；IP 维度仍保留总量窗口防止轮换账号。
    login_account_limiter.reset(account_key)

    if needs_upgrade:
        hashed = hash_password(account.password, enforce_policy=False)
        model = Admin if account.role == "管理员" else User
        await model.filter(id=user.id).update(password=hashed, must_change_password=True)
        user.must_change_password = True

    token = create_access_token({
        "id": user.id,
        "username": user.username,
        "role": account.role,
        "token_version": int(getattr(user, "token_version", 0)),
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
async def register(account: RegisterRequest, request: Request):
    if not register_ip_limiter.allow(_client_ip(request)):
        raise HTTPException(status_code=429, detail="注册请求过于频繁，请稍后再试")
    if await User.get_or_none(username=account.username) is not None:
        raise CustomException("账号重复")
    validate_password(account.password)
    try:
        await User.create(
            username=account.username,
            password=hash_password(account.password),
            name=account.name or account.username,
            avatar=account.avatar,
            role="用户",
            must_change_password=False,
        )
    except IntegrityError as exc:
        # DB 唯一约束是并发注册的最终防线。
        raise CustomException("账号重复") from exc
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
        raise CustomException("新密码不能与原密码相同")
    validate_password(account.newPassword)
    await model.filter(id=user_id).update(
        password=hash_password(account.newPassword),
        must_change_password=False,
        token_version=int(getattr(user, "token_version", 0)) + 1,
    )
    return Result.success()
