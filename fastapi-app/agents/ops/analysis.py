"""商品四维分析引擎：评价 / 销量 / 库存 / 综合表现。

与 insights.py 同一哲学：事实全部由 SQL + 确定性规则产出，LLM 只负责表述。
情感与评分为规则判定（星级为主、词典辅助），可单测、可复现、无外部依赖。"""
import asyncio
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from models import Goods, Orders, Review
from common.time import format_store_time, utc_now
from pypika_tortoise.functions import Date as SqlDate
from tortoise.functions import Count, Function, Sum

from .insights import _count_keywords

# ---- 情感词典（差评聚焦与 3 星内容修正用；星级是主判据）----
_POSITIVE_TERMS = (
    "好吃", "美味", "新鲜", "喜欢", "满意", "推荐", "精致", "好看", "细腻",
    "香甜", "快", "好评", "赞", "回购", "惊喜", "完美", "生日快乐", "划算",
)
_NEGATIVE_TERMS = (
    "难吃", "太甜", "太腻", "不新鲜", "失望", "太小", "太贵", "太慢", "太硬",
    "坏了", "漏了", "化了", "踩雷", "不值", "差评", "量少", "服务差", "不建议",
)
# 否定前缀：命中的正向词实际表达负向情感，不计入正向
_NEGATION_PREFIX = ("不", "没", "别", "不太", "不是很")

GOOD_STOCK_DAYS = (7, 30)  # 库存可售天数理想区间


class DateOnly(Function):
    """Portable DATE(column) expression supported by MySQL and SQLite."""

    database_func = SqlDate


def _hits(text: str, terms: tuple) -> int:
    return sum(1 for t in terms if t in text)


def _positive_hits(text: str) -> int:
    """排除被否定的正向词（如"不好吃"不命中"好吃"）。"""
    return sum(
        1 for t in _POSITIVE_TERMS
        if t in text and not any(text[max(0, text.index(t) - 2):text.index(t)].endswith(n) for n in _NEGATION_PREFIX)
    )


def classify_sentiment(rating: int | None, content: str) -> str:
    """好评/中评/差评。星级为主判据；3 星参考内容词典修正。"""
    if rating is None:
        rating = 3
    if rating >= 4:
        return "差评" if _hits(content, _NEGATIVE_TERMS) >= 1 else "好评"
    if rating <= 2:
        return "差评"
    # 3 星：词典定夺，无信号归中评
    if _hits(content, _NEGATIVE_TERMS) >= 1:
        return "差评"
    if _positive_hits(content) >= 1:
        return "好评"
    return "中评"


def _since(days: int) -> datetime:
    return utc_now() - timedelta(days=days)


async def _load_sales_snapshot(goods_id: int | None, days: int) -> dict:
    """Load one reusable SQL-aggregated order snapshot for an analysis request."""
    current_query = Orders.filter(time__gte=_since(days), status__not="已取消")
    current_job = (
        current_query.annotate(
            order_count=Count("id"), total_qty=Sum("num"), total_revenue=Sum("total_price"),
        )
        .group_by("goods_id")
        .values("goods_id", "order_count", "total_qty", "total_revenue")
    )
    jobs = [current_job, Goods.all().order_by("id")]
    if goods_id is not None:
        jobs.extend([
            (
                Orders.filter(
                    goods_id=goods_id,
                    time__gte=_since(days * 2),
                    time__lt=_since(days),
                    status__not="已取消",
                )
                .annotate(total_qty=Sum("num"))
                .values("total_qty")
            ),
            (
                current_query.filter(goods_id=goods_id)
                .annotate(day=DateOnly("time"), total_qty=Sum("num"))
                .group_by("day")
                .values("day", "total_qty")
            ),
        ])
    values = await asyncio.gather(*jobs)
    aggregates, goods_rows = values[0], values[1]
    return {
        "days": days,
        "goods_id": goods_id,
        "goods": {goods.id: goods for goods in goods_rows},
        "sales": {row["goods_id"]: row for row in aggregates if row["goods_id"] is not None},
        "previous_qty": int((values[2][0].get("total_qty") or 0) if goods_id is not None and values[2] else 0),
        "daily": values[3] if goods_id is not None else [],
    }


# ==================== 评价分析 ====================

async def review_analysis(goods_id: int, days: int = 30) -> dict:
    reviews = await Review.filter(
        goods_id=goods_id, time__gte=_since(days),
    ).prefetch_related("user").order_by("-id")
    goods = await Goods.get_or_none(id=goods_id)

    sentiment_counts = Counter()
    negative_details = []
    for r in reviews:
        content = (r.content or "").strip()
        sentiment = classify_sentiment(r.rating, content)
        sentiment_counts[sentiment] += 1
        if sentiment == "差评":
            negative_details.append({
                "rating": r.rating,
                "content": content,
                "user_name": r.user.name if r.user else "—",
                "time": format_store_time(r.time),
            })

    # 差评聚焦：差评原文中的负向词频次（定位问题类型：太甜/太小/物流…）
    neg_terms = Counter()
    for item in negative_details:
        for t in _NEGATIVE_TERMS:
            if t in item["content"]:
                neg_terms[t] += 1

    total = len(reviews)
    positive = sentiment_counts.get("好评", 0)

    # 真实好评摘录（供 AI 分析引用真实用户声音，与差评摘录对称）
    positive_details = []
    for r in reviews:
        content = (r.content or "").strip()
        if classify_sentiment(r.rating, content) == "好评" and content:
            positive_details.append({
                "rating": r.rating,
                "content": content,
                "time": format_store_time(r.time),
            })

    return {
        "goods_id": goods_id,
        "goods_name": goods.name if goods else "—",
        "days": days,
        "total": total,
        "avg_rating": round(sum(r.rating or 0 for r in reviews) / total, 2) if total else 0,
        "sentiment": {k: sentiment_counts.get(k, 0) for k in ("好评", "中评", "差评")},
        "positive_rate": round(positive / total * 100, 1) if total else 0,
        "keywords": _count_keywords([(r.content or "") for r in reviews], top_n=10),
        "negative_focus": [{"term": t, "count": c} for t, c in neg_terms.most_common(8)],
        "negative_reviews": negative_details[:10],
        "positive_reviews": positive_details[:3],
    }


# ==================== 销量分析 ====================

async def sales_analysis(goods_id: int | None = None, days: int = 30) -> dict:
    """单商品趋势 或 全店热销/滞销排行（goods_id=None 时）。"""
    snapshot = await _load_sales_snapshot(goods_id, days)
    return _sales_from_snapshot(snapshot, goods_id)


def _sales_from_snapshot(snapshot: dict, goods_id: int | None) -> dict:
    days = snapshot["days"]
    sales_by_goods = snapshot["sales"]
    all_goods = snapshot["goods"]
    if goods_id is not None:
        row = sales_by_goods.get(goods_id, {})
        qty = int(row.get("total_qty") or 0)
        revenue = Decimal(row.get("total_revenue") or 0)
        trend_counter = {
            item["day"].isoformat() if hasattr(item["day"], "isoformat") else str(item["day"])[:10]:
            int(item.get("total_qty") or 0)
            for item in snapshot["daily"] if item.get("day")
        }
        today = datetime.now(timezone.utc).date()
        trend = []
        for offset in range(days - 1, -1, -1):
            day = (today - timedelta(days=offset)).isoformat()
            trend.append({"date": day, "qty": trend_counter.get(day, 0)})

        prev_qty = snapshot["previous_qty"]
        goods = all_goods.get(goods_id)
        return {
            "goods_id": goods_id,
            "goods_name": goods.name if goods else "—",
            "days": days,
            "order_count": int(row.get("order_count") or 0),
            "total_qty": qty,
            "total_revenue": float(revenue),
            "prev_total_qty": prev_qty,
            "qty_change_pct": round((qty - prev_qty) / prev_qty * 100, 1) if prev_qty else None,
            "daily_trend": trend,
        }

    qty_by_goods = {
        item_goods_id: int(row.get("total_qty") or 0)
        for item_goods_id, row in sales_by_goods.items()
    }

    def _row(goods_id: int, qty: int) -> dict:
        g = all_goods.get(goods_id)
        return {
            "goods_id": goods_id,
            "name": g.name if g else f"#{goods_id}",
            "qty": qty,
            "stock": g.num if g else 0,
            "price": float(g.price) if g and g.price is not None else 0,
        }

    ranked = sorted(
        (_row(gid, qty) for gid, qty in qty_by_goods.items()),
        key=lambda row: row["qty"], reverse=True,
    )
    hot = ranked[:10]
    # 滞销：窗口内销量最低但仍有库存的商品（含零销量）
    with_stock = [
        _row(g.id, qty_by_goods.get(g.id, 0))
        for g in all_goods.values() if (g.num or 0) > 0
    ]
    slow = sorted(with_stock, key=lambda r: (r["qty"], -r["stock"]))[:10]
    return {
        "goods_id": None,
        "days": days,
        "order_count": sum(int(row.get("order_count") or 0) for row in sales_by_goods.values()),
        "total_qty": sum(qty_by_goods.values()),
        "total_revenue": float(sum(Decimal(row.get("total_revenue") or 0) for row in sales_by_goods.values())),
        "hot_ranking": hot,
        "slow_ranking": slow,
    }


# ==================== 库存分析 ====================

def stock_level(num: int | None) -> str:
    if num is None or num <= 0:
        return "售罄"
    if num <= 5:
        return "紧张"
    if num <= 15:
        return "偏低"
    return "健康"


def inventory_score(stock: int, sold_qty: int, days: int) -> int:
    """库存健康分 0-100：可售天数落在 GOOD_STOCK_DAYS 内为满分。

    售罄且有销量 = 补货紧急；库存巨大且无销量 = 占压资金。
    纯函数，便于单测。"""
    if stock <= 0:
        return 20 if sold_qty > 0 else 50
    if sold_qty <= 0:
        return 40  # 有货无人买，滞销占压
    days_of_stock = stock / (sold_qty / days)
    low, high = GOOD_STOCK_DAYS
    if low <= days_of_stock <= high:
        return 100
    if days_of_stock < low:
        # 低于 7 天线性衰减到 50
        return int(50 + 50 * days_of_stock / low)
    # 高于 30 天线性衰减，90 天以上保底 60
    return max(60, int(100 - 40 * (days_of_stock - high) / 60))


async def inventory_analysis(days: int = 30) -> dict:
    return _inventory_from_snapshot(await _load_sales_snapshot(None, days))


def _inventory_from_snapshot(snapshot: dict) -> dict:
    days = snapshot["days"]
    all_goods = sorted(snapshot["goods"].values(), key=lambda goods: goods.num)
    qty_by_goods = {
        goods_id: int(row.get("total_qty") or 0)
        for goods_id, row in snapshot["sales"].items()
    }

    items = []
    level_counter: Counter = Counter()
    warning = []
    for g in all_goods:
        num = g.num or 0
        level = stock_level(num)
        level_counter[level] += 1
        sold = qty_by_goods.get(g.id, 0)
        row = {
            "goods_id": g.id,
            "name": g.name,
            "stock": num,
            "unit": g.unit or "个",
            "level": level,
            "sold_qty": sold,
            "days_of_stock": round(num / (sold / days), 1) if sold else None,
            "inventory_value": round(float(num * (g.price or 0)), 2),
        }
        items.append(row)
        # 预警：售罄/紧张，或库存可售天数不足 3 天且窗口内有销量
        urgent = (num == 0 and sold > 0) or (0 < num <= 5) or (
            sold > 0 and row["days_of_stock"] is not None and row["days_of_stock"] < 3
        )
        if urgent:
            warning.append(row)

    return {
        "days": days,
        "total_goods": len(all_goods),
        "levels": {k: level_counter.get(k, 0) for k in ("健康", "偏低", "紧张", "售罄")},
        "total_inventory_value": round(sum(i["inventory_value"] for i in items), 2),
        "warning_count": len(warning),
        "warning_list": warning[:15],
        "items": items,
    }


# ==================== 综合表现（评价 × 销量 × 库存联动） ====================

def composite_score(avg_rating: float, review_count: int,
                    goods_qty: int, top_qty: int,
                    stock: int, sold_qty: int, days: int) -> dict:
    """综合表现评分，纯函数。

    销量分 40%：相对窗口内销量冠军归一化；
    评价分 40%：星级折算 + 样本量置信（不足 5 条向中性 60 收缩）；
    库存分 20%：inventory_score。
    无评价时评价分给中性 60 并标注，避免新品被误判为差。"""
    sales_score = min(100, round(goods_qty / top_qty * 100)) if top_qty > 0 else 0
    raw_review = (avg_rating / 5) * 100 if review_count else 60
    confidence = min(1.0, review_count / 5) if review_count else 0
    review_score = round(60 + (raw_review - 60) * confidence)
    inv_score = inventory_score(stock, sold_qty, days)
    total = round(sales_score * 0.4 + review_score * 0.4 + inv_score * 0.2)
    grade = "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D"

    suggestions = []
    if review_count == 0:
        suggestions.append("暂无评价数据，评价分为中性基准，建议引导首批买家评价")
    if avg_rating and avg_rating < 4 and review_count >= 3:
        suggestions.append("评价均分偏低，优先排查差评聚焦的问题类型")
    if sold_qty == 0:
        suggestions.append("窗口内零销量，考虑促销或优化商品页")
    elif stock <= 5:
        suggestions.append("库存紧张且有持续销量，建议尽快补货")
    if stock > 0 and sold_qty > 0:
        dos = stock / (sold_qty / days)
        if dos > 30:
            suggestions.append("库存可售天数超过 30 天，存在占压风险")
    if not suggestions:
        suggestions.append("各维度表现均衡，保持当前运营节奏")

    return {
        "total": total,
        "grade": grade,
        "dimensions": {
            "sales": {"score": sales_score, "weight": 0.4},
            "review": {"score": review_score, "weight": 0.4},
            "inventory": {"score": inv_score, "weight": 0.2},
        },
        "suggestions": suggestions,
    }


async def product_performance(goods_id: int, days: int = 30) -> dict:
    snapshot, reviews = await asyncio.gather(
        _load_sales_snapshot(goods_id, days), review_analysis(goods_id, days),
    )
    sales = _sales_from_snapshot(snapshot, goods_id)
    return _performance_from_snapshot(snapshot, reviews, sales, goods_id)


def _performance_from_snapshot(snapshot: dict, reviews: dict, sales: dict, goods_id: int) -> dict:
    days = snapshot["days"]
    goods = snapshot["goods"].get(goods_id)
    top_qty = max(
        (int(row.get("total_qty") or 0) for row in snapshot["sales"].values()),
        default=0,
    )

    stock = goods.num or 0 if goods else 0
    score = composite_score(
        avg_rating=reviews["avg_rating"],
        review_count=reviews["total"],
        goods_qty=sales["total_qty"],
        top_qty=top_qty,
        stock=stock,
        sold_qty=sales["total_qty"],
        days=days,
    )
    return {
        "goods_id": goods_id,
        "goods_name": sales["goods_name"],
        "days": days,
        "stock": stock,
        "score": score,
    }


async def build_product_fact_snapshot(goods_id: int, days: int = 30) -> dict:
    """Build every product-analysis fact from one reusable order snapshot."""
    snapshot, reviews = await asyncio.gather(
        _load_sales_snapshot(goods_id, days), review_analysis(goods_id, days),
    )
    sales = _sales_from_snapshot(snapshot, goods_id)
    return {
        "performance": _performance_from_snapshot(snapshot, reviews, sales, goods_id),
        "reviews": reviews,
        "sales": sales,
        "inventory": _inventory_from_snapshot(snapshot),
    }


__all__ = [
    "build_product_fact_snapshot",
    "classify_sentiment",
    "composite_score",
    "inventory_analysis",
    "inventory_score",
    "product_performance",
    "review_analysis",
    "sales_analysis",
    "stock_level",
]
