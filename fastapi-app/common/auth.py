"""JWT 认证与密码哈希模块"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from common.exception_handler import CustomException
from settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from models import Admin, User

oauth2_scheme = HTTPBearer()

# bcrypt 硬限制：密码只取前 72 字节，超长部分被静默截断。
# 与其静默截断（用户以为长密码更安全），不如在入口明确拒绝。
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_CHARS = 8
COMMON_PASSWORDS = {
    "12345678", "password", "password1", "qwerty123", "admin123", "11111111",
}


def validate_password(plaintext: str) -> None:
    if len(plaintext) < MIN_PASSWORD_CHARS:
        raise CustomException(f"密码至少需要 {MIN_PASSWORD_CHARS} 个字符")
    if len(plaintext.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise CustomException(f"密码过长：最多 {MAX_PASSWORD_BYTES} 字节（中文每字占 3 字节）")
    if plaintext.lower() in COMMON_PASSWORDS:
        raise CustomException("密码过于常见，请使用更难猜测的密码")


def hash_password(plaintext: str, *, enforce_policy: bool = True) -> str:
    """生成 bcrypt 哈希。

    enforce_policy=False 只用于把历史明文密码升级为哈希；账号会同时
    被标记强制改密，不会成为弱密码策略的后门。
    """
    if enforce_policy:
        validate_password(plaintext)
    data = plaintext.encode("utf-8")
    if len(data) > MAX_PASSWORD_BYTES:
        raise CustomException(f"密码过长：最多 {MAX_PASSWORD_BYTES} 字节")
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode()


def verify_password(plaintext: str, stored: str) -> tuple:
    """校验密码，返回 (is_valid, needs_upgrade)。
    needs_upgrade 为 True 表示密码是明文匹配的，需要升级为 bcrypt。
    """
    encoded = plaintext.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False, False
    data = encoded

    # 先尝试 bcrypt 验证
    try:
        if bcrypt.checkpw(data, stored.encode()):
            return True, False
    except (ValueError, TypeError):
        pass

    # 明文比对（兼容未迁移的旧密码）
    if plaintext == stored:
        return True, True

    return False, False


def create_access_token(user: dict) -> str:
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        # 密码修改/重置时数据库版本递增，旧 Token 立即失效。
        "token_version": int(user.get("token_version", 0)),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),  # utcnow() 在 3.12+ 已弃用
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        result = {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "role": payload.get("role"),
            "token_version": payload.get("token_version"),
        }
        if (
            not isinstance(result["user_id"], int)
            or result["role"] not in {"用户", "管理员"}
            or not isinstance(result["token_version"], int)
        ):
            return None
        return result
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> dict:
    payload = verify_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    # 服务端存在性校验：JWT 无状态，用户被硬删除后其 Token 在过期前仍有效
    #（当前配置最长 2 小时），这 2 小时是越权窗口。这里用一次主键查询把窗口
    # 关到零；代价是每请求一条 EXISTS 语句，走主键索引，成本可接受。
    model = Admin if payload["role"] == "管理员" else User
    account = await model.get_or_none(id=payload["user_id"])
    if account is None:
        raise HTTPException(status_code=401, detail="账号不存在或已被删除")
    if int(getattr(account, "token_version", 0)) != payload["token_version"]:
        raise HTTPException(status_code=401, detail="登录凭证已失效，请重新登录")
    if bool(getattr(account, "must_change_password", False)) and request.url.path != "/updatePassword":
        raise HTTPException(status_code=403, detail="请先修改初始密码")
    return payload


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "管理员":
        raise HTTPException(status_code=403, detail="无管理员权限")
    return current_user


async def get_current_customer(current_user: dict = Depends(get_current_user)) -> dict:
    """仅允许普通用户进入个人交易写路径。

    Admin 与 User 是独立表，数字主键可能重叠。若只检查“已登录”，
    管理员 id=1 就可能把订单/收藏/地址写到普通用户 id=1 名下。
    """
    if current_user["role"] != "用户":
        raise HTTPException(status_code=403, detail="该操作仅限普通用户")
    return current_user
