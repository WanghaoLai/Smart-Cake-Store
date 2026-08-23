"""订单站内通知：状态变更事务内的同步写行（roadmap 改进项 6）。

通知即业务副产物——与状态变更同事务，保证"状态变了必有通知"，
无需独立 outbox 表。只对买家不可自行感知的流转发通知：
发货（管理员操作）与取消（涉及退款/库存）；用户自己确认收货不发。"""
from domain.order_status import ORDER_CANCELLED, ORDER_SHIPPED

from models import Notification

# 订单只能由普通用户下单（get_current_customer 网关），接收者角色固定
NOTIFICATION_OWNER_ROLE = "用户"


async def notify_order_event(order, goods_name: str | None) -> None:
    """按订单目标状态写一条买家通知。在状态变更事务内调用。

    非通知类流转（如 待评价）静默跳过——调用方无需分支判断。"""
    if order.status == ORDER_SHIPPED:
        await Notification.create(
            user_id=order.user_id,
            owner_role=NOTIFICATION_OWNER_ROLE,
            type="order.shipped",
            title="订单已发货",
            content=f"您的订单 {order.order_no}（{_label(goods_name, order.num)}）已发货，请留意配送。",
        )
    elif order.status == ORDER_CANCELLED:
        await Notification.create(
            user_id=order.user_id,
            owner_role=NOTIFICATION_OWNER_ROLE,
            type="order.cancelled",
            title="订单已取消",
            content=f"您的订单 {order.order_no}（{_label(goods_name, order.num)}）已取消，库存已恢复。如非本人操作请联系客服。",
        )


def _label(goods_name: str | None, num) -> str:
    name = goods_name or "商品"
    return f"{name} × {num}"
