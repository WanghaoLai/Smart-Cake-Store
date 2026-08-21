"""Authenticated order reads and transactional order mutations."""

from tortoise.transactions import in_transaction

from models import Goods, Orders


ORDER_PENDING = "待发货"
ORDER_SHIPPED = "已发货"
ORDER_CANCELLED = "已取消"
CANCELLABLE_STATUSES = {ORDER_PENDING, ORDER_SHIPPED}


def _order_total(order) -> object:
    """成交价快照优先；旧单无快照时回退当前商品价（商品已删则为 0）。"""
    if order.total_price is not None:
        return order.total_price
    if order.goods:
        return order.goods.price * order.num
    return 0


async def get_order_status(user_id: int, order_id: int = None, order_no: str = None) -> str:
    if order_id or order_no:
        filters = {"id": order_id} if order_id else {"order_no": order_no}
        order = await Orders.filter(user_id=user_id, **filters).prefetch_related("goods", "address").first()
        if not order:
            return "未找到该订单，请确认订单号是否正确。"
        return (
            f"订单号：{order.order_no or 'N/A'}\n"
            f"- 商品：{order.goods.name if order.goods else '未知'}\n"
            f"- 数量：{order.num}\n"
            f"- 单价：¥{order.goods.price if order.goods else '未知'}\n"
            f"- 总价：¥{_order_total(order)}\n"
            f"- 收货地址：{order.address.address if order.address else '未知'}\n"
            f"- 下单时间：{order.time}\n"
            f"- 状态：{order.status or '待发货'}"
        )

    orders = await Orders.filter(user_id=user_id).prefetch_related("goods").order_by("-id").limit(10)
    if not orders:
        return "您目前没有订单。"
    lines = [f"您最近的 {len(orders)} 笔订单："]
    for order in orders:
        goods_name = order.goods.name if order.goods else "未知"
        total = _order_total(order)
        status = order.status or "待发货"
        lines.append(f"- 订单号 {order.order_no or 'N/A'}：{goods_name} x{order.num}，¥{total}，{order.time}，{status}")
    return "\n".join(lines)


async def cancel_order(user_id: int, order_id: int = None, order_no: str = None) -> str:
    if not (order_id or order_no):
        return "请提供订单ID或订单号。"
    async with in_transaction():
        filters = {"id": order_id} if order_id else {"order_no": order_no}
        order = await Orders.filter(user_id=user_id, **filters).select_for_update().first()
        if not order:
            return "未找到该订单，无法取消。请确认订单号是否正确。"

        if order.status == ORDER_CANCELLED:
            return f"订单 {order.order_no or order.id} 已经取消，无需重复操作。"
        if order.status not in CANCELLABLE_STATUSES:
            return f"订单 {order.order_no or order.id} 当前状态为“{order.status}”，不能取消。"

        if not order.goods_id:
            return "订单缺少商品信息，为避免库存不一致，暂时无法取消，请联系人工客服。"
        goods = await Goods.filter(id=order.goods_id).select_for_update().first()
        if not goods:
            return "订单对应商品不存在，为避免库存不一致，暂时无法取消，请联系人工客服。"
        goods.num += order.num
        await goods.save(update_fields=["num"])
        order_label = order.order_no or order.id
        order.status = ORDER_CANCELLED
        await order.save(update_fields=["status"])
    return f"订单 {order_label} 已成功取消，{goods.name}的库存已恢复。"


__all__ = ["cancel_order", "get_order_status"]
