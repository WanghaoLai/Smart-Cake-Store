"""JWT 认证与密码哈希模块"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from common.exception_handler import CustomException
from settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from models import Admin, User

oauth2_scheme = HTTPBearer()

# bcrypt 硬限制：密码只取前 72 字节，超长部分被静默截断。
# 与其静默截断（用户以为长密码更安全），不如在入口明确拒绝。
MAX_PASSWORD_BYTES = 72


def validate_password(plaintext: str) -> None:
    if len(plaintext.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise CustomException(f"密码过长：最多 {MAX_PASSWORD_BYTES} 字节（中文每字占 3 字节）")


def hash_password(plaintext: str) -> str:
    data = plaintext.encode("utf-8")[:72]
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode()


def verify_password(plaintext: str, stored: str) -> tuple:
    """校验密码，返回 (is_valid, needs_upgrade)。
    needs_upgrade 为 True 表示密码是明文匹配的，需要升级为 bcrypt。
    """
    data = plaintext.encode("utf-8")[:72]

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
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),  # utcnow() 在 3.12+ 已弃用
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "role": payload.get("role"),
        }
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> dict:
    payload = verify_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    # 服务端存在性校验：JWT 无状态，用户被硬删除后其 Token 在过期前仍有效
    #（当前配置最长 2 小时），这 2 小时是越权窗口。这里用一次主键查询把窗口
    # 关到零；代价是每请求一条 EXISTS 语句，走主键索引，成本可接受。
    model = Admin if payload["role"] == "管理员" else User
    if not await model.filter(id=payload["user_id"]).exists():
        raise HTTPException(status_code=401, detail="账号不存在或已被删除")
    return payload


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "管理员":
        raise HTTPException(status_code=403, detail="无管理员权限")
    return current_user
