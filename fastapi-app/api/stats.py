from fastapi import APIRouter, Depends

from common.auth import get_current_user
from common.result import Result
from models import Goods, Orders, Notice, Favorite

router = APIRouter(prefix="/stats", dependencies=[Depends(get_current_user)])


@router.get("/home")
async def home_stats(current_user: dict = Depends(get_current_user)):
    """首页数据看板：根据当前用户角色返回不同维度的统计数据"""
    role = current_user["role"]
    user_id = current_user["user_id"]

    if role == "管理员":
        goods_count = await Goods.all().count()
        orders_count = await Orders.all().count()
        # 低库存预警（库存 ≤ 5）
        low_stock = await Goods.filter(num__lte=5).count()
        # 总销售额：所有订单总价
        orders_with_goods = await Orders.all().prefetch_related("goods")
        revenue = sum(
            (o.goods.price * o.num) if o.goods else 0
            for o in orders_with_goods
        )
        # 最近 5 条公告
        notices = await Notice.all().order_by("-id").limit(5)
        # 最近 6 笔订单
        recent_orders_qs = await Orders.all().order_by("-id").limit(6).prefetch_related("goods", "user")
        recent_orders = [
            {
                "id": o.id,
                "order_no": o.order_no,
                "goodsName": o.goods.name if o.goods else "—",
                "goodsImg": o.goods.img if o.goods else None,
                "num": o.num,
                "user": u.name if (u := o.user) else "—",
                "time": o.time,
            }
            for o in recent_orders_qs
        ]
        return Result.success({
            "role": role,
            "cards": [
                {"key": "goods", "label": "商品总数", "value": goods_count, "icon": "Goods", "color": "primary", "suffix": "件"},
                {"key": "orders", "label": "订单总数", "value": orders_count, "icon": "SoldOut", "color": "accent", "suffix": "单"},
                {"key": "revenue", "label": "销售总额", "value": round(revenue, 2), "icon": "Money", "color": "success", "prefix": "¥"},
                {"key": "lowStock", "label": "低库存预警", "value": low_stock, "icon": "WarningFilled", "color": "warning", "suffix": "项"},
            ],
            "notices": [{"id": n.id, "name": n.name, "content": n.content, "time": n.time} for n in notices],
            "recentOrders": recent_orders,
        })

    # 普通用户
    my_orders = await Orders.filter(user_id=user_id).count()
    my_favs = await Favorite.filter(user_id=user_id).count()
    pending = await Orders.filter(user_id=user_id).count()  # 当前未区分状态，全部视为进行中
    # 累计消费
    my_orders_qs = await Orders.filter(user_id=user_id).prefetch_related("goods")
    spent = sum((o.goods.price * o.num) if o.goods else 0 for o in my_orders_qs)
    # 推荐：取库存 > 0 的前 4 件最新商品
    recommend_qs = await Goods.filter(num__gt=0).order_by("-id").limit(4).prefetch_related("category")
    recommends = [
        {
            "id": g.id, "name": g.name, "img": g.img, "price": g.price,
            "unit": g.unit, "description": g.description,
            "categoryName": g.category.name if g.category else None,
        }
        for g in recommend_qs
    ]
    # 公告
    notices = await Notice.all().order_by("-id").limit(4)
    return Result.success({
        "role": role,
        "cards": [
            {"key": "orders", "label": "我的订单", "value": my_orders, "icon": "SoldOut", "color": "primary", "suffix": "单"},
            {"key": "favs", "label": "我的收藏", "value": my_favs, "icon": "Star", "color": "accent", "suffix": "件"},
            {"key": "spent", "label": "累计消费", "value": round(spent, 2), "icon": "Money", "color": "success", "prefix": "¥"},
            {"key": "pending", "label": "进行中", "value": pending, "icon": "Timer", "color": "warning", "suffix": "单"},
        ],
        "notices": [{"id": n.id, "name": n.name, "content": n.content, "time": n.time} for n in notices],
        "recommends": recommends,
    })
