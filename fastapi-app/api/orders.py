from datetime import datetime
import random
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction

from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Orders, Goods

router = APIRouter(prefix="/orders", dependencies=[Depends(get_current_user)])

# 订单状态常量：集中定义，避免魔法字符串散落各文件
ORDER_PENDING = "待发货"
ORDER_SHIPPED = "已发货"
# "已签收"语义上等同于"待评价"（签收后等待评价）；为兼容历史数据保留常量，
# 但新流转不再使用，迁移脚本会把历史 已签收 回填为 待评价
ORDER_RECEIVED = "已签收"
ORDER_PENDING_REVIEW = "待评价"
ORDER_REVIEWED = "已评价"
ORDER_CANCELLED = "已取消"

# 状态机：(角色, 当前状态, 目标状态) -> 允许
# 取消订单时由 update_status 内部统一恢复库存，调用方无需关心
ALLOWED_TRANSITIONS = {
    ("管理员", ORDER_PENDING, ORDER_SHIPPED),
    ("管理员", ORDER_PENDING, ORDER_CANCELLED),
    # 用户确认签收 = 进入待评价；评价提交完成后由 /reviews/add 推进到 已评价
    ("用户", ORDER_SHIPPED, ORDER_PENDING_REVIEW),
    ("用户", ORDER_RECEIVED, ORDER_PENDING_REVIEW),
    ("用户", ORDER_PENDING, ORDER_CANCELLED),
    ("用户", ORDER_SHIPPED, ORDER_CANCELLED),
}

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


@router.post("/add")
async def add(orders_pydantic: OrdersCreatePydantic, current_user: dict = Depends(get_current_user)):
    if orders_pydantic.goods_id is None:
        raise CustomException("请选择要购买的商品")
    if orders_pydantic.num is None or orders_pydantic.num <= 0:
        raise CustomException("购买数量必须大于 0")

    now = datetime.now()
    order_no = now.strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))
    time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    # 库存校验、订单写入、库存扣减必须在同一事务同一行锁内完成，否则并发超卖
    async with in_transaction():
        goods = await Goods.filter(id=orders_pydantic.goods_id).select_for_update().first()
        if goods is None:
            raise CustomException("商品不存在")
        if goods.num < orders_pydantic.num:
            raise CustomException(f"库存不足，剩余 {goods.num} {goods.unit or '个'}")

        await Orders.create(
            user_id=current_user["user_id"],
            goods_id=orders_pydantic.goods_id,
            address_id=orders_pydantic.address_id,
            num=orders_pydantic.num,
            time=time_str,
            order_no=order_no,
            status=ORDER_PENDING,
        )
        goods.num -= orders_pydantic.num
        await goods.save(update_fields=['num'])

    return Result.success()


@router.delete("/delete/{id}")
async def delete(id: int, current_user: dict = Depends(get_current_user)):
    # 归属校验 + 库存恢复 + 订单删除原子化
    async with in_transaction():
        order = await Orders.filter(id=id).select_for_update().first()
        if order is None:
            raise CustomException("订单不存在")
        if current_user["role"] != "管理员" and order.user_id != current_user["user_id"]:
            raise CustomException("无权操作该订单")

        # 已取消的订单在状态变更时已恢复过库存，这里避免二次回补
        if order.status != ORDER_CANCELLED and order.goods_id:
            goods = await Goods.filter(id=order.goods_id).select_for_update().first()
            if goods:
                goods.num += order.num
                await goods.save(update_fields=['num'])

        await Orders.filter(id=id).delete()

    return Result.success()


@router.put("/update_status/{id}")
async def update_status(id: int, status: str, current_user: dict = Depends(get_current_user)):
    """订单状态变更：按 (角色, 当前状态, 目标状态) 状态机校验。
    取消订单在同一事务内恢复库存，与 delete 路径互不重叠。"""
    status = (status or "").strip()
    if not status:
        raise CustomException("目标状态不能为空")

    async with in_transaction():
        order = await Orders.filter(id=id).select_for_update().first()
        if order is None:
            raise CustomException("订单不存在")
        if current_user["role"] != "管理员" and order.user_id != current_user["user_id"]:
            raise CustomException("无权操作该订单")

        key = (current_user["role"], order.status, status)
        if key not in ALLOWED_TRANSITIONS:
            raise CustomException(f"当前状态({order.status})不允许变更为({status})")

        # 仅"已取消"是终态需要回补库存；其他正向流转不动库存
        if status == ORDER_CANCELLED and order.status != ORDER_CANCELLED and order.goods_id:
            goods = await Goods.filter(id=order.goods_id).select_for_update().first()
            if goods:
                goods.num += order.num
                await goods.save(update_fields=['num'])

        order.status = status
        await order.save(update_fields=['status'])

    return Result.success()


@router.get("/selectPage")
async def select(goodsName: str = "", userId: int = 0, status: str = "",
                 pageNum: int = 1, pageSize: int = 5,
                 current_user: dict = Depends(get_current_user)):
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
            "goodsName": orders.goods.name if orders.goods else None,
            "goodsUnit": orders.goods.unit if orders.goods else None,
            "goodsImg": orders.goods.img if orders.goods else None,
            "goodsPrice": orders.goods.price if orders.goods else None,
            "total": orders.goods.price * orders.num if orders.goods else None,
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
