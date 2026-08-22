"""个性化推荐引擎：纯规则、无 LLM。

信号优先级（计划 §2.1）：收藏分类 > 历史购买分类 > 商品平均评分 > 销量热度。
单店用户量与交互密度不足以训练协同过滤/深度模型——规则版已能利用全部现有信号，
且每条推荐可解释（reason 字段）。冷启动（无收藏无订单）回退销量 Top N。"""
import logging
import math

from tortoise.functions import Avg, Count

from models import Favorite, Goods, Orders, Review
from settings import RECOMMEND_WEIGHTS

logger = logging.getLogger(__name__)

ORDER_CANCELLED = "已取消"
DEFAULT_RATING = 3.0  # 无评价商品的先验分（3/5 中性偏保守，不奖励无数据商品）


async def _rating_map() -> dict:
    rows = await (
        Review.all()
        .annotate(score=Avg("rating"))
        .group_by("goods_id")
        .values("goods_id", "score")
    )
    return {row["goods_id"]: float(row["score"]) for row in rows if row["score"] is not None}


async def _category_preferences(user_id: int) -> tuple:
    """返回 (分类总分, 收藏分类集合, 购买分类集合, 已收藏商品 id 集)。

    分开跟踪收藏/购买命中的分类：文案归因要区分"因为收藏"与"因为买过"，
    总分混在一起会让 reason 说错话。"""
    weights = RECOMMEND_WEIGHTS
    cat_score: dict = {}
    fav_cats: set = set()
    buy_cats: set = set()
    fav_goods_ids: set = set()

    favs = await Favorite.filter(user_id=user_id).prefetch_related("goods")
    for fav in favs:
        if fav.goods is not None:
            fav_goods_ids.add(fav.goods.id)
            if fav.goods.category_id:
                fav_cats.add(fav.goods.category_id)
                cat_score[fav.goods.category_id] = (
                    cat_score.get(fav.goods.category_id, 0) + weights["favorite_category"]
                )

    orders = await Orders.filter(user_id=user_id).exclude(
        status=ORDER_CANCELLED
    ).prefetch_related("goods")
    for order in orders:
        if order.goods is not None and order.goods.category_id:
            buy_cats.add(order.goods.category_id)
            cat_score[order.goods.category_id] = (
                cat_score.get(order.goods.category_id, 0) + weights["purchase_category"]
            )

    return cat_score, fav_cats, buy_cats, fav_goods_ids, bool(favs or orders)


async def recommend(user_id: int, limit: int = 4) -> list:
    """为用户生成个性化推荐，返回与首页推荐卡片兼容的 dict 列表（附 reason）。"""
    from .semantic_search import sales_map

    cat_score, fav_cats, buy_cats, fav_goods_ids, has_behavior = await _category_preferences(user_id)
    # 已收藏的商品不重复推荐（收藏列表里已有，推荐应服务于发现新商品）
    candidates = [
        g for g in await Goods.filter(num__gt=0).prefetch_related("category")
        if g.id not in fav_goods_ids
    ]
    if not candidates:
        return []

    sales = await sales_map()
    ratings = await _rating_map()
    weights = RECOMMEND_WEIGHTS
    max_sales = max((sales.get(g.id, 0) for g in candidates), default=0)

    scored = []
    for goods in candidates:
        cat_pref = cat_score.get(goods.category_id, 0)
        rating = ratings.get(goods.id, DEFAULT_RATING)
        # 销量在候选集内归一化（0~1），避免绝对值压过分类偏好
        sales_norm = sales.get(goods.id, 0) / max_sales if max_sales > 0 else 0.0

        if not has_behavior:
            # 冷启动：纯热度排序（替换旧"时间 Top N"）
            score = sales_norm
            reason = f"热销 {sales.get(goods.id, 0)} 单" if sales.get(goods.id, 0) else "新品上架"
        else:
            score = (
                cat_pref
                + weights["rating"] * (rating / 5.0)
                + weights["sales"] * sales_norm
            )
            if goods.category_id in fav_cats:
                reason = "基于你的收藏偏好"
            elif goods.category_id in buy_cats:
                reason = "基于你的购买历史"
            elif ratings.get(goods.id) is not None:
                reason = f"好评均分 {rating:.1f}"
            else:
                reason = "热门商品"
        scored.append((score, reason, goods))

    scored.sort(key=lambda t: (-t[0], -t[2].id))
    return [
        {
            "id": goods.id,
            "name": goods.name,
            "img": goods.img,
            "price": goods.price,
            "unit": goods.unit,
            "description": goods.description,
            "categoryName": goods.category.name if goods.category else None,
            "reason": reason,
        }
        for score, reason, goods in scored[:limit]
    ]
