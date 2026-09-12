from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction

from common.audit import client_ip
from common.auth import get_current_customer, get_current_user
from common.exception_handler import ConflictException, CustomException, ForbiddenException, NotFoundException
from common.pagination import clamp_page
from common.result import Result, PageInfo
from common.time import format_store_time
from models import AuditLog, Goods, Orders
from domain.purchase import shipping
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
        for name, field in OrdersPydantic.model_fields.items() if name != "spec"
    },
    request_id=(str, Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")),
    spec=(str, Field(default="", max_length=255)),
    user_id=(Optional[int], Field(None, alias="userId")),
    goods_id=(Optional[int], Field(None, alias="goodsId")),
    address_id=(Optional[int], Field(None, alias="addressId")),
)


@router.post("/add")
async def add(orders_pydantic: OrdersCreatePydantic, current_user: dict = Depends(get_current_customer)):
    if orders_pydantic.goods_id is None:
        raise CustomException("请选择要购买的商品")
    if orders_pydantic.num is None or orders_pydantic.num <= 0:
        raise CustomException("购买数量必须大于 0")
    if orders_pydantic.address_id is None:
        raise CustomException("请选择收货地址")

    from domain.purchase import purchase
    return Result.success(await purchase(current_user["user_id"], orders_pydantic.request_id,
        address_id=orders_pydantic.address_id, goods_id=orders_pydantic.goods_id,
        num=orders_pydantic.num, spec=orders_pydantic.spec))


@router.delete("/delete/{id}")
async def delete(id: int, current_user: dict = Depends(get_current_user), request: Request = None):
    from domain.order_cancellation import cancel_purchase
    await cancel_purchase(current_user, order_id=id, ip=client_ip(request))
    return Result.success()


@router.put("/update_status/{id}")
async def update_status(id: int, status: str, current_user: dict = Depends(get_current_user), request: Request = None):
    """订单状态变更：按 (角色, 当前状态, 目标状态) 状态机校验。
    取消订单在同一事务内恢复库存，与 delete 路径互不重叠。"""
    status = (status or "").strip()
    if not status:
        raise CustomException("目标状态不能为空")

    if status == ORDER_CANCELLED:
        return await delete(id, current_user, request)

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
        if status == ORDER_SHIPPED and order.goods_id:
            # 发货通知需要商品名；查询失败不阻断状态变更（通知内容降级为"商品"）
            goods = await Goods.get_or_none(id=order.goods_id)
            goods_name = goods.name if goods else None

        from_status = order.status
        order.status = status
        await order.save(update_fields=['status'])
        await notify_order_event(order, goods_name)
        await AuditLog.create(
            operator_role=current_user["role"], operator_id=current_user["user_id"],
            operator_name=current_user.get("username"), action="order.status_change",
            target_type="order", target_id=id,
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
            "aName": shipping(orders).get("name"),
            "aAddress": shipping(orders).get("address"),
            "aPhone": shipping(orders).get("phone"),
            "userName": orders.user.name if orders.user else None,
        }
        for orders in orders_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=orders_list)
    return Result.success(pageinfo)
