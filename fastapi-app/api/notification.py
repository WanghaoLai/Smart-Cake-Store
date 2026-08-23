"""订单站内通知 API：列表 / 未读数 / 全部已读。

归属由 角色 + user_id 联合标识（User/Admin 主键可能重叠，与
Conversation 同一模型）；读取侧轮询，分钟级实时性足够。"""
from fastapi import APIRouter, Depends

from common.auth import get_current_user
from common.pagination import clamp_page
from common.result import Result, PageInfo
from common.time import format_store_time
from models import Notification

router = APIRouter(prefix="/notification", dependencies=[Depends(get_current_user)])


def _owner_filter(current_user: dict) -> dict:
    return {"user_id": current_user["user_id"], "owner_role": current_user["role"]}


@router.get("/list")
async def list_notifications(
    pageNum: int = 1, pageSize: int = 10,
    current_user: dict = Depends(get_current_user),
):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = Notification.filter(**_owner_filter(current_user))
    total = await query.count()
    rows = await query.order_by("-id").offset((pageNum - 1) * pageSize).limit(pageSize)
    items = [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "isRead": n.is_read,
            "createdAt": format_store_time(n.created_at),
        }
        for n in rows
    ]
    return Result.success(PageInfo(total=total, list=items))


@router.get("/unread-count")
async def unread_count(current_user: dict = Depends(get_current_user)):
    count = await Notification.filter(**_owner_filter(current_user), is_read=False).count()
    return Result.success({"count": count})


@router.put("/read-all")
async def read_all(current_user: dict = Depends(get_current_user)):
    await Notification.filter(**_owner_filter(current_user), is_read=False).update(is_read=True)
    return Result.success()
