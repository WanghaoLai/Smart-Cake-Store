"""Single source of truth for the order lifecycle."""

ORDER_PENDING = "待发货"
ORDER_SHIPPED = "已发货"
ORDER_RECEIVED = "已签收"  # legacy value accepted during migration
ORDER_PENDING_REVIEW = "待评价"
ORDER_REVIEWED = "已评价"
ORDER_CANCELLED = "已取消"

# 当前系统没有退货、配送拦截和商品验收状态。只有尚未发货的订单能够直接
# 撤销、退款并恢复为可售库存；已发货订单必须由未来的独立售后流程处理。
CANCELLABLE_STATUSES = frozenset({ORDER_PENDING})

ALLOWED_TRANSITIONS = frozenset({
    ("管理员", ORDER_PENDING, ORDER_SHIPPED),
    ("管理员", ORDER_PENDING, ORDER_CANCELLED),
    ("用户", ORDER_SHIPPED, ORDER_PENDING_REVIEW),
    ("用户", ORDER_RECEIVED, ORDER_PENDING_REVIEW),
    ("用户", ORDER_PENDING, ORDER_CANCELLED),
})

__all__ = [
    "ALLOWED_TRANSITIONS", "CANCELLABLE_STATUSES", "ORDER_CANCELLED",
    "ORDER_PENDING", "ORDER_PENDING_REVIEW", "ORDER_RECEIVED",
    "ORDER_REVIEWED", "ORDER_SHIPPED",
]
