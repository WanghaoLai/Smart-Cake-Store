"""Authenticated order reads and transactional order mutations."""

from models import Orders
from domain.purchase import shipping
from common.time import format_store_time


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
            f"- 规格：{order.spec or '默认'}\n"
            f"- 单价：¥{order.goods.price if order.goods else '未知'}\n"
            f"- 总价：¥{_order_total(order)}\n"
            f"- 收货地址：{shipping(order).get('address') or '未知'}\n"
            f"- 下单时间：{format_store_time(order.time)}\n"
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
        lines.append(f"- 订单号 {order.order_no or 'N/A'}：{goods_name} x{order.num}，¥{total}，{format_store_time(order.time)}，{status}")
    return "\n".join(lines)


async def cancel_order(user_id: int, order_id: int = None, order_no: str = None) -> str:
    if not (order_id or order_no):
        return "请提供订单ID或订单号。"
    from domain.order_cancellation import cancel_purchase
    from common.exception_handler import CustomException
    try:
        order, changed, refunded = await cancel_purchase({"role":"用户", "user_id":user_id},
            order_id=order_id, order_no=order_no)
    except CustomException as exc:
        return exc.message
    if not changed:
        return f"订单 {order.order_no} 已经取消。" + ("余额已补退。" if refunded else "无需重复操作。")
    return f"订单 {order.order_no} 已成功取消，库存已恢复。" + ("款项已退回余额。" if refunded else "")


__all__ = ["cancel_order", "get_order_status"]
