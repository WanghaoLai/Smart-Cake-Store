"""认证相关 Pydantic 模型"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str


class UserInfo(BaseModel):
    id: int
    username: str
    name: str | None = None
    avatar: str | None = None
    role: str | None = None


class TokenResponse(BaseModel):
    token: str
    user: UserInfo
