"""智能客服工具集"""
from tortoise.transactions import in_transaction

from models import Orders, Goods

TOOL_DEFINITIONS = """
- get_order_status: 查询当前用户的订单状态。参数：order_id(订单ID，可选), order_no(订单号，可选)，都不传则查所有订单
- cancel_order: 取消当前用户的指定订单。参数：order_id(订单ID，可选), order_no(订单号，可选)
- recommend_cake: 推荐蛋糕。参数：preference(偏好描述，可选，如"生日""情侣""送朋友"等)
- check_stock: 查询蛋糕库存。参数：goods_name(蛋糕名称关键词，可选，不传则查所有库存)
"""


async def get_order_status(user_id: int, order_id: int = None, order_no: str = None) -> str:
    if order_id or order_no:
        if order_id:
            order = await Orders.filter(id=order_id, user_id=user_id).prefetch_related("goods", "address").first()
        else:
            order = await Orders.filter(order_no=order_no, user_id=user_id).prefetch_related("goods", "address").first()
        if not order:
            return f"未找到该订单，请确认订单号是否正确。"
        return (
            f"订单号：{order.order_no or 'N/A'}\n"
            f"- 商品：{order.goods.name if order.goods else '未知'}\n"
            f"- 数量：{order.num}\n"
            f"- 单价：¥{order.goods.price if order.goods else '未知'}\n"
            f"- 总价：¥{order.goods.price * order.num if order.goods else 0}\n"
            f"- 收货地址：{order.address.address if order.address else '未知'}\n"
            f"- 下单时间：{order.time}\n"
            f"- 状态：待发货"
        )

    orders = await Orders.filter(user_id=user_id).prefetch_related("goods").order_by("-id").limit(10)
    if not orders:
        return "您目前没有订单。"

    lines = [f"您最近的 {len(orders)} 笔订单："]
    for o in orders:
        goods_name = o.goods.name if o.goods else "未知"
        total = o.goods.price * o.num if o.goods else 0
        lines.append(f"- 订单号 {o.order_no or 'N/A'}：{goods_name} x{o.num}，¥{total}，{o.time}")
    return "\n".join(lines)


async def cancel_order(user_id: int, order_id: int = None, order_no: str = None) -> str:
    if not (order_id or order_no):
        return "请提供订单ID或订单号。"

    # 库存恢复 + 订单删除必须在同一事务同一行锁内完成，防止并发恢复错乱
    async with in_transaction():
        if order_id:
            order = await Orders.filter(id=order_id, user_id=user_id).select_for_update().first()
        else:
            order = await Orders.filter(order_no=order_no, user_id=user_id).select_for_update().first()

        if not order:
            return "未找到该订单，无法取消。请确认订单号是否正确。"

        goods_name = None
        if order.goods_id:
            goods = await Goods.filter(id=order.goods_id).select_for_update().first()
            if goods:
                goods.num += order.num
                await goods.save(update_fields=['num'])
                goods_name = goods.name

        order_label = order.order_no or order.id
        await Orders.filter(id=order.id).delete()

    return f"订单 {order_label} 已成功取消，{goods_name or '商品'} 库存已恢复。"


async def recommend_cake(preference: str = "") -> str:
    query = Goods.filter()
    if preference:
        goods_list = await Goods.filter(name__contains=preference).limit(5)
        if not goods_list:
            goods_list = await Goods.filter(description__contains=preference).limit(5)
    else:
        goods_list = await Goods.all().limit(5)

    if not goods_list:
        goods_list = await Goods.all().limit(5)

    lines = ["为您推荐以下蛋糕："]
    for i, g in enumerate(goods_list, 1):
        stock_info = "有货" if g.num > 0 else "暂时售罄"
        lines.append(f"{i}. {g.name} - ¥{g.price}（{stock_info}，剩余{g.num}{g.unit or '个'}）\n   {g.description}")
    return "\n".join(lines)


async def check_stock(goods_name: str = "") -> str:
    if goods_name:
        goods_list = await Goods.filter(name__contains=goods_name)
    else:
        goods_list = await Goods.all()

    if not goods_list:
        return f"未找到与「{goods_name}」相关的蛋糕。"

    lines = ["当前蛋糕库存："] if not goods_name else [f"「{goods_name}」相关蛋糕库存："]
    for g in goods_list:
        status = "充足" if g.num > 10 else ("紧张" if g.num > 0 else "售罄")
        lines.append(f"- {g.name}：剩余 {g.num} {g.unit or '个'}（{status}）")
    return "\n".join(lines)


TOOLS_MAP = {
    "get_order_status": get_order_status,
    "cancel_order": cancel_order,
    "recommend_cake": recommend_cake,
    "check_stock": check_stock,
}
