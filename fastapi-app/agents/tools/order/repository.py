"""Authenticated order reads and transactional order mutations."""

from tortoise.transactions import in_transaction

from models import Goods, Orders


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
            f"- 总价：¥{order.goods.price * order.num if order.goods else 0}\n"
            f"- 收货地址：{order.address.address if order.address else '未知'}\n"
            f"- 下单时间：{order.time}\n"
            "- 状态：待发货"
        )

    orders = await Orders.filter(user_id=user_id).prefetch_related("goods").order_by("-id").limit(10)
    if not orders:
        return "您目前没有订单。"
    lines = [f"您最近的 {len(orders)} 笔订单："]
    for order in orders:
        goods_name = order.goods.name if order.goods else "未知"
        total = order.goods.price * order.num if order.goods else 0
        lines.append(f"- 订单号 {order.order_no or 'N/A'}：{goods_name} x{order.num}，¥{total}，{order.time}")
    return "\n".join(lines)


async def cancel_order(user_id: int, order_id: int = None, order_no: str = None) -> str:
    if not (order_id or order_no):
        return "请提供订单ID或订单号。"
    async with in_transaction():
        filters = {"id": order_id} if order_id else {"order_no": order_no}
        order = await Orders.filter(user_id=user_id, **filters).select_for_update().first()
        if not order:
            return "未找到该订单，无法取消。请确认订单号是否正确。"

        goods_name = None
        if order.goods_id:
            goods = await Goods.filter(id=order.goods_id).select_for_update().first()
            if goods:
                goods.num += order.num
                await goods.save(update_fields=["num"])
                goods_name = goods.name
        order_label = order.order_no or order.id
        await Orders.filter(id=order.id).delete()
    return f"订单 {order_label} 已成功取消，{goods_name or '商品'} 库存已恢复。"


__all__ = ["cancel_order", "get_order_status"]
