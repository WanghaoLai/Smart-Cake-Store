from datetime import datetime
import random
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator

from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Orders, Goods

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


@router.post("/add")
async def add(orders_pydantic: OrdersCreatePydantic, current_user: dict = Depends(get_current_user)):
    create_data = orders_pydantic.model_dump(exclude_unset=True, exclude={'id', 'user_id'})
    create_data['user_id'] = current_user["user_id"]
    now = datetime.now()
    create_data['time'] = now.strftime('%Y-%m-%d %H:%M:%S')
    create_data['order_no'] = now.strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))
    await Orders.create(**create_data)
    # 更新一下商品表的库存
    goods = await Goods.filter(id=orders_pydantic.goods_id).first()
    goods.num = goods.num - orders_pydantic.num
    await goods.save()
    return Result.success()


@router.delete("/delete/{id}")
async def delete(id: int, current_user: dict = Depends(get_current_user)):
    order = await Orders.filter(id=id).prefetch_related("goods").first()
    if order is None:
        raise CustomException("订单不存在")
    if current_user["role"] != "管理员" and order.user_id != current_user["user_id"]:
        raise CustomException("无权操作该订单")
    if order.goods:
        order.goods.num += order.num
        await order.goods.save()
    await Orders.filter(id=id).delete()
    return Result.success()


@router.get("/selectPage")
async def select(goodsName: str = "", userId: int = 0,  pageNum: int = 1, pageSize: int = 5,
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

