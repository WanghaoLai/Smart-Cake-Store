"""当前登录账号的个人资料接口。"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result
from models import Admin, User

router = APIRouter(prefix="/account", dependencies=[Depends(get_current_user)])


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None


@router.put("/profile")
async def update_profile(data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    name = (data.name or "").strip()
    if not name:
        raise CustomException("姓名不能为空")
    if len(name) > 255:
        raise CustomException("姓名不能超过 255 个字符")
    model = Admin if current_user["role"] == "管理员" else User
    updated = await model.filter(id=current_user["user_id"]).update(name=name, avatar=data.avatar)
    if not updated:
        raise CustomException("账号不存在")
    return Result.success()
