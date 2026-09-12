"""All cancellation entry points share one transaction and lock order: user -> order -> goods."""
from tortoise.transactions import in_transaction
from common.exception_handler import CustomException, ForbiddenException, NotFoundException, ConflictException
from domain.order_status import ALLOWED_TRANSITIONS, ORDER_CANCELLED
from domain.notifications import notify_order_event
from models import Orders, Goods, User, WalletTransaction, AuditLog

async def cancel_purchase(operator: dict, *, order_id=None, order_no=None, ip=None):
    filters = {"id": order_id} if order_id is not None else {"order_no": order_no}
    if operator.get("role") not in {"用户", "管理员"}:
        raise ForbiddenException()
    if operator["role"] != "管理员":
        filters["user_id"] = operator["user_id"]
    candidate = await Orders.filter(**filters).first()
    if candidate is None:
        raise NotFoundException("未找到该订单，无法取消")
    async with in_transaction():
        user = await User.filter(id=candidate.user_id).select_for_update().first()
        if user is None:
            raise CustomException("订单用户不存在，无法退款")
        order = await Orders.filter(**filters).select_for_update().first()
        if order is None or order.user_id != user.id:
            raise NotFoundException("订单不存在")
        previous = order.status
        changed = previous != ORDER_CANCELLED
        if changed:
            if (operator["role"], previous, ORDER_CANCELLED) not in ALLOWED_TRANSITIONS:
                raise ConflictException(f"当前状态({previous})不允许取消")
            goods = await Goods.filter(id=order.goods_id).select_for_update().first() if order.goods_id else None
            if goods is None:
                raise CustomException("订单商品不存在，为避免库存不一致，无法安全取消")
            goods.num += order.num
            await goods.save(update_fields=["num"])
            order.status = ORDER_CANCELLED
            await order.save(update_fields=["status"])
            await notify_order_event(order, goods.name)
        # Also repair historical cancelled paid orders without repeating inventory restoration.
        paid = await WalletTransaction.filter(order_id=order.id, type="payment").first()
        refunded = False
        if paid and paid.amount < 0 and not await WalletTransaction.filter(order_id=order.id, type="refund").exists():
            amount = -paid.amount
            user.balance += amount
            await user.save(update_fields=["balance"])
            await WalletTransaction.create(user_id=user.id, type="refund", amount=amount,
                balance_after=user.balance, order_id=order.id, request_id=f"refund:{order.id}",
                remark=f"订单 {order.order_no} 取消退款")
            refunded = True
        if changed or refunded:
            await AuditLog.create(operator_role=operator["role"], operator_id=operator["user_id"],
                operator_name=operator.get("username"), action="order.cancel", target_type="order",
                target_id=order.id, detail={"order_no":order.order_no,"from":previous,"refunded":refunded}, ip=ip)
    return order, changed, refunded
