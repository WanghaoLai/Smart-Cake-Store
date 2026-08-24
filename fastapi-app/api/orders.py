import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from common.audit import client_ip, record_audit
from common.auth import get_current_customer, get_current_user
from common.exception_handler import ConflictException, CustomException, ForbiddenException, NotFoundException
from common.pagination import clamp_page
from common.result import Result, PageInfo
from common.time import STORE_TIMEZONE, format_store_time, utc_now
from models import Address, Goods, Orders, User, WalletTransaction
from domain.notifications import notify_order_event
from domain.order_status import (
    ALLOWED_TRANSITIONS,
    ORDER_CANCELLED,
    ORDER_PENDING,
    ORDER_PENDING_REVIEW,
    ORDER_RECEIVED,
    ORDER_REVIEWED,
    ORDER_SHIPPED,
)

router = APIRouter(prefix="/orders", dependencies=[Depends(get_current_user)])

# 创建 pydantic 只读模型 把数据库模型转化成pydantic模型
OrdersPydantic = pydantic_model_creator(Orders)
# 自动生成所有字段为 Optional 的更新模型
OrdersCreatePydantic = create_model(
    "OrdersCreatePydantic",
    **{
        # 从只读模型中读取所有字段然后给它设置成可选
        name: (Optional[field.annotation], None)
        for name, field in OrdersPydantic.model_fields.items()
    },
    user_id=(Optional[int], Field(None, alias="userId")),
    goods_id=(Optional[int], Field(None, alias="goodsId")),
    address_id=(Optional[int], Field(None, alias="addressId")),
)


def _generate_order_no() -> str:
    """秒级时间戳（可读、便于客服按时间定位）+ 6 位 hex 随机（同秒碰撞概率 ~6e-8）。
    唯一性最终由 DB 唯一索引保证，生成端只需尽力降低碰撞。"""
    return utc_now().astimezone(STORE_TIMEZONE).strftime('%Y%m%d%H%M%S') + uuid.uuid4().hex[:6].upper()


async def _refund_wallet(order: Orders) -> bool:
    """在调用方事务中退回已支付订单；旧订单或已退款订单保持幂等。"""
    paid = await WalletTransaction.filter(order_id=order.id, type="payment").first()
    if paid is None:
        return False
    if await WalletTransaction.filter(order_id=order.id, type="refund").exists():
        return False
    user = await User.filter(id=order.user_id).select_for_update().first()
    if user is None:
        raise CustomException("订单用户不存在，无法退款")
    amount = -paid.amount
    user.balance += amount
    await user.save(update_fields=["balance"])
    await WalletTransaction.create(
        user_id=user.id,
        type="refund",
        amount=amount,
        balance_after=user.balance,
        order_id=order.id,
        request_id=f"refund:{order.id}",
        remark=f"订单 {order.order_no} 取消退款",
    )
    return True


@router.post("/add")
async def add(orders_pydantic: OrdersCreatePydantic, current_user: dict = Depends(get_current_customer)):
    if orders_pydantic.goods_id is None:
        raise CustomException("请选择要购买的商品")
    if orders_pydantic.num is None or orders_pydantic.num <= 0:
        raise CustomException("购买数量必须大于 0")
    if orders_pydantic.address_id is None:
        raise CustomException("请选择收货地址")

    created_at = utc_now()

    # 库存校验、订单写入、库存扣减必须在同一事务同一行锁内完成，否则并发超卖。
    # 订单号撞上唯一索引（概率极低）时整体重试一次：换新号重新走完整事务，
    # 重试包含库存扣减故不会二次扣减（上一轮事务已回滚）。
    for _ in range(2):
        try:
            async with in_transaction():
                # 地址是订单中的 PII 边界：必须同时按 id + 当前用户查询，
                # 不能先按 id 查再在应用层“相信”客户端传入的 userId。
                address = await Address.get_or_none(
                    id=orders_pydantic.address_id,
                    user_id=current_user["user_id"],
                )
                if address is None:
                    raise ForbiddenException("收货地址不存在或不属于当前用户")
                # 固定按“商品 -> 用户”顺序加锁；取消订单也使用同一顺序，降低死锁概率。
                goods = await Goods.filter(id=orders_pydantic.goods_id).select_for_update().first()
                if goods is None:
                    raise NotFoundException("商品不存在")
                if goods.num < orders_pydantic.num:
                    raise ConflictException(f"库存不足，剩余 {goods.num} {goods.unit or '个'}")
                user = await User.filter(id=current_user["user_id"]).select_for_update().first()
                if user is None:
                    raise NotFoundException("用户不存在")

                total = goods.price * orders_pydantic.num
                if user.balance < total:
                    shortage = total - user.balance
                    raise ConflictException(
                        f"余额不足，订单需 ¥{total:.2f}，当前余额 ¥{user.balance:.2f}，还差 ¥{shortage:.2f}"
                    )

                order = await Orders.create(
                    user_id=current_user["user_id"],
                    goods_id=orders_pydantic.goods_id,
                    address_id=orders_pydantic.address_id,
                    num=orders_pydantic.num,
                    time=created_at,
                    order_no=_generate_order_no(),
                    status=ORDER_PENDING,
                    # 下单即锁定成交价，改价不影响历史订单
                    total_price=total,
                )
                goods.num -= orders_pydantic.num
                await goods.save(update_fields=['num'])
                user.balance -= total
                await user.save(update_fields=['balance'])
                await WalletTransaction.create(
                    user_id=user.id,
                    type="payment",
                    amount=-total,
                    balance_after=user.balance,
                    order_id=order.id,
                    request_id=f"payment:{order.id}",
                    remark=f"支付订单 {order.order_no}",
                )
            break
        except IntegrityError:
            continue
    else:
        raise CustomException("订单号生成冲突，请重试")

    return Result.success({"order_no": order.order_no, "balance": user.balance})


@router.delete("/delete/{id}")
async def delete(id: int, current_user: dict = Depends(get_current_user), request: Request = None):
    """兼容历史 DELETE 契约，但不再物理删除订单。

    订单是资金、库存与评价的审计根：物理删除任意状态的订单会
    同时擦除历史并错误回补库存。因此该端点现在仅执行与 update_status
    相同的“取消”语义；已取消时幂等成功，其他终态明确拒绝。
    """
    async with in_transaction():
        order = await Orders.filter(id=id).select_for_update().first()
        if order is None:
            raise NotFoundException("订单不存在")
        if current_user["role"] != "管理员" and order.user_id != current_user["user_id"]:
            raise ForbiddenException("无权操作该订单")

        if order.status == ORDER_CANCELLED:
            return Result.success()

        from_status = order.status
        key = (current_user["role"], order.status, ORDER_CANCELLED)
        if key not in ALLOWED_TRANSITIONS:
            raise ConflictException(f"当前状态({order.status})不允许取消")

        if not order.goods_id:
            raise CustomException("订单缺少商品信息，无法安全恢复库存")
        goods = await Goods.filter(id=order.goods_id).select_for_update().first()
        if goods is None:
            raise CustomException("订单商品不存在，无法安全取消")
        goods.num += order.num
        await goods.save(update_fields=['num'])

        await _refund_wallet(order)

        order.status = ORDER_CANCELLED
        await order.save(update_fields=['status'])
        # 通知即业务副产物：与状态变更同事务，状态变了必有通知
        await notify_order_event(order, goods.name)

    await record_audit(
        current_user, "order.cancel", "order", id,
        detail={"order_no": order.order_no, "from": from_status},
        ip=client_ip(request),
    )
    return Result.success()


@router.put("/update_status/{id}")
async def update_status(id: int, status: str, current_user: dict = Depends(get_current_user), request: Request = None):
    """订单状态变更：按 (角色, 当前状态, 目标状态) 状态机校验。
    取消订单在同一事务内恢复库存，与 delete 路径互不重叠。"""
    status = (status or "").strip()
    if not status:
        raise CustomException("目标状态不能为空")

    async with in_transaction():
        order = await Orders.filter(id=id).select_for_update().first()
        if order is None:
            raise NotFoundException("订单不存在")
        if current_user["role"] != "管理员" and order.user_id != current_user["user_id"]:
            raise ForbiddenException("无权操作该订单")

        key = (current_user["role"], order.status, status)
        if key not in ALLOWED_TRANSITIONS:
            raise ConflictException(f"当前状态({order.status})不允许变更为({status})")

        # 仅"已取消"是终态需要回补库存；其他正向流转不动库存
        goods_name = None
        if status == ORDER_CANCELLED and order.status != ORDER_CANCELLED and order.goods_id:
            goods = await Goods.filter(id=order.goods_id).select_for_update().first()
            if goods:
                goods.num += order.num
                await goods.save(update_fields=['num'])
                goods_name = goods.name
            await _refund_wallet(order)
        elif status == ORDER_SHIPPED and order.goods_id:
            # 发货通知需要商品名；查询失败不阻断状态变更（通知内容降级为"商品"）
            goods = await Goods.get_or_none(id=order.goods_id)
            goods_name = goods.name if goods else None

        from_status = order.status
        order.status = status
        await order.save(update_fields=['status'])
        await notify_order_event(order, goods_name)

    # 审计在事务提交后 best-effort 记录：状态机拒绝时不留审计噪声
    await record_audit(
        current_user, "order.status_change", "order", id,
        detail={"order_no": order.order_no, "from": from_status, "to": status},
        ip=client_ip(request),
    )
    return Result.success()


@router.get("/selectPage")
async def select(goodsName: str = "", userId: int = 0, status: str = "",
                 pageNum: int = 1, pageSize: int = 5,
                 current_user: dict = Depends(get_current_user)):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    # 普通用户强制仅能查自己的订单，防止越权查询他人订单
    if current_user["role"] != "管理员":
        userId = current_user["user_id"]
    # 同时获取分页数据和总数
    query = Orders.filter()
    if userId > 0:
        query = query.filter(user_id=userId)
    if goodsName and goodsName != '':
        query = query.filter(goods__name__contains=goodsName)
    if status and status != '':
        query = query.filter(status=status)

    query = query.prefetch_related("address", "user", "goods")
    # 获取分页数据
    orders_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    orders_list = [
        {
            **OrdersPydantic.model_validate(orders).model_dump(),  # id=xxx,no=xxx,name=xxx
            "time": format_store_time(orders.time),
            "goodsName": orders.goods.name if orders.goods else None,
            "goodsUnit": orders.goods.unit if orders.goods else None,
            "goodsImg": orders.goods.img if orders.goods else None,
            "goodsPrice": orders.goods.price if orders.goods else None,
            # 优先成交价快照；无快照且商品已删除的旧单回退当前价（历史兼容）
            "total": orders.total_price
            if orders.total_price is not None
            else (orders.goods.price * orders.num if orders.goods else None),
            "aName": orders.address.name if orders.address else None,
            "aAddress": orders.address.address if orders.address else None,
            "aPhone": orders.address.phone if orders.address else None,
            "userName": orders.user.name if orders.user else None,
        }
        for orders in orders_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=orders_list)
    return Result.success(pageinfo)
