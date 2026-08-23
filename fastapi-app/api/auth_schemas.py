"""认证相关 Pydantic 模型。"""
from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str
    name: str | None = None
    avatar: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str
    role: Literal["用户", "管理员"]


class PasswordUpdateRequest(BaseModel):
    password: str
    newPassword: str


class UserInfo(BaseModel):
    id: int
    username: str
    name: str | None = None
    avatar: str | None = None
    role: str | None = None


class TokenResponse(BaseModel):
    token: str
    user: UserInfo
