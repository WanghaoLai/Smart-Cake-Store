"""JWT 认证与密码哈希模块"""
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS

oauth2_scheme = HTTPBearer()


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
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
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
    return payload


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "管理员":
        raise HTTPException(status_code=403, detail="无管理员权限")
    return current_user
