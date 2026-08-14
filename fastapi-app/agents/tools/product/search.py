"""Read-only product search, ranking, recommendation and stock queries."""
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from models import Favorite, Goods, Orders, Review


# ==================== 文本相关性打分（Grounding 与工具共享） ====================

_QUERY_NOISE = set("的了吗呢啊呀有是和与或请问一下帮我看看想要需要推荐商品蛋糕")
_PREFERENCE_GROUPS = (
    (("长辈", "老人", "父母", "爷爷", "奶奶", "祝寿"),
     ("长辈", "祝寿", "福寿", "安康", "低脂", "温润", "老少")),
    (("孩子", "儿童", "小朋友", "宝宝"),
     ("孩子", "儿童", "童趣", "卡通", "童心", "孩童")),
    (("情侣", "恋人", "爱人", "纪念日", "告白"),
     ("情侣", "恋人", "爱心", "纪念日", "告白", "热恋")),
    (("朋友", "同事", "聚会", "团建"),
     ("朋友", "同事", "聚会", "聚餐", "团建", "职场")),
    (("女生", "女朋友", "闺蜜"), ("女生", "仙女", "浪漫")),
    (("男生", "男朋友", "男士"), ("男生", "男士", "潮酷", "沉稳")),
)


def _relevance(query: str, text: str) -> int:
    """Small deterministic ranker combining exact / ngram / preference signals.

    Same algorithm is shared by Grounding (get_product_facts) and the
    recommend_cake tool, so tool output and grounding evidence never diverge.
    """
    normalized_query = re.sub(r"[^0-9a-zA-Z一-鿿]", "", query.lower())
    normalized_text = text.lower()
    useful = {char for char in normalized_query if char not in _QUERY_NOISE}
    overlap = sum(1 for char in useful if char in normalized_text)
    exact_bonus = 100 if normalized_query and normalized_query in normalized_text else 0
    ngrams = {
        normalized_query[index:index + size]
        for size in (2, 3, 4)
        for index in range(max(0, len(normalized_query) - size + 1))
    }
    phrase_score = sum(len(phrase) ** 2 for phrase in ngrams if phrase in normalized_text)
    preference_score = 0
    for triggers, signals in _PREFERENCE_GROUPS:
        if any(trigger in normalized_query for trigger in triggers):
            preference_score += 30 * sum(signal in normalized_text for signal in signals)
    return exact_bonus + phrase_score + preference_score + overlap


# ==================== 个性化打分 ====================
#
# 权重校准原则：
#   - _relevance 量级：exact_bonus 100、phrase_score 0~120、preference 30*N
#   - 个性化量级：分类命中 40 + 收藏 25 + 评价 ±20（rating 1~5 → -20~+20）
#   - 强文本命中（≈200）仍压过纯个性化（≈85），个性化在并列时拉新顺序；
#   - 无任何信号时（匿名用户、空订单/收藏/评价）个性化分量为 0，退化为纯文本排序。
WEIGHT_CATEGORY_MATCH = 40   # 用户最近购买分类命中
WEIGHT_FAVORITE = 25         # 用户收藏命中
WEIGHT_RATING_PER_STAR = 10  # 评价均分相对基线 3 分的权重
RATING_BASELINE = 3
RECENT_ORDERS_FOR_PROFILE = 3


@dataclass(frozen=True)
class UserProfile:
    """Per-user preference signals aggregated from MySQL.

    Each field degrades gracefully (empty) when the user has no data so that
    the ranker falls back to pure text relevance.
    """
    recent_category_ids: frozenset[int]
    favorite_goods_ids: frozenset[int]
    rating_by_goods: dict[int, float]


async def _load_user_profile(user_id: int | None) -> UserProfile | None:
    """Return None for anonymous users so the caller can skip personalization.

    For authenticated users, three signals are pulled in parallel-friendly
    sequence: recent order categories, favorite goods ids, and per-goods
    rating averages (computed in Python; rating rows are bounded by review
    count which is small for this domain).
    """
    if user_id is None:
        return None

    recent_orders = await (
        Orders.filter(user_id=user_id)
        .order_by("-id")
        .limit(RECENT_ORDERS_FOR_PROFILE)
        .prefetch_related("goods")
    )
    recent_category_ids = frozenset(
        order.goods.category_id
        for order in recent_orders
        if order.goods_id is not None
        and order.goods is not None
        and order.goods.category_id is not None
    )

    favorite_goods_ids = frozenset(
        await Favorite.filter(user_id=user_id).values_list("goods_id", flat=True)
    )

    review_rows = await Review.all().values("goods_id", "rating")
    rating_buckets: dict[int, list[float]] = {}
    for row in review_rows:
        goods_id = row.get("goods_id")
        rating = row.get("rating")
        if goods_id is None or rating is None:
            continue
        rating_buckets.setdefault(goods_id, []).append(float(rating))
    rating_by_goods = {
        goods_id: sum(values) / len(values)
        for goods_id, values in rating_buckets.items()
    }

    return UserProfile(
        recent_category_ids=recent_category_ids,
        favorite_goods_ids=favorite_goods_ids,
        rating_by_goods=rating_by_goods,
    )


def _personalization_score(row: dict, profile: UserProfile) -> float:
    """Per-row bonus added on top of _relevance.

    Returns 0 when every signal is empty, which means the row keeps its pure
    text-relevance score and the ranker behaves identically to anonymous mode.
    """
    score = 0.0
    if row.get("category_id") in profile.recent_category_ids:
        score += WEIGHT_CATEGORY_MATCH
    if row.get("id") in profile.favorite_goods_ids:
        score += WEIGHT_FAVORITE
    avg_rating = profile.rating_by_goods.get(row.get("id"))
    if avg_rating is not None:
        score += (avg_rating - RATING_BASELINE) * WEIGHT_RATING_PER_STAR
    return score


# ==================== 结构化查询 ====================


class RecommendationQuery(BaseModel):
    """Structured recommendation input.

    `search_text()` composes a single string so that _PREFERENCE_GROUPS
    triggers fire on `occasion` and `audience` exactly like the legacy path,
    while `max_price` and `in_stock_only` are applied as hard filters.
    """
    keywords: str = Field(default="", max_length=100, description="口味、原料、商品名等关键词")
    occasion: str | None = Field(default=None, description="送礼场景：长辈/孩子/情侣/朋友/聚会")
    audience: str | None = Field(default=None, description="目标受众：女生/男生/女朋友/闺蜜")
    max_price: float | None = Field(default=None, ge=0, description="预算上限（含），未明确时留空")
    in_stock_only: bool = Field(default=True, description="True 仅返回有库存商品")

    def search_text(self) -> str:
        parts = [self.keywords.strip(), (self.occasion or "").strip(), (self.audience or "").strip()]
        return " ".join(part for part in parts if part)


# ==================== 候选检索 + 排序 ====================


async def search_products(
    query: str,
    limit: int = 8,
    in_stock_only: bool = False,
) -> tuple[list[dict], int]:
    """Load bounded candidate pool from MySQL, attach _relevance + category_id.

    Returning _relevance on each row lets downstream rankers (e.g.
    recommend_cake) combine text score with personalization without
    recomputing it.
    """
    rows = await Goods.all().limit(200).values(
        "id", "name", "price", "num", "unit", "description", "category_id"
    )
    if in_stock_only:
        rows = [row for row in rows if row["num"] > 0]
    for row in rows:
        row["_relevance"] = _relevance(query, f"{row['name']} {row.get('description') or ''}")
    ranked = sorted(
        rows,
        key=lambda row: (row["_relevance"], row["num"] > 0, -row["id"]),
        reverse=True,
    )[:limit]
    return ranked, len(rows)


async def get_product_facts(query: str, limit: int = 8) -> str:
    """Return bounded, current product facts directly from MySQL."""
    ranked, total = await search_products(query, limit)
    if not ranked:
        return "当前商品库为空。"
    lines = [f"MySQL 当前共有 {total} 个可查询商品；以下为与问题最相关的 {len(ranked)} 个："]
    for row in ranked:
        description = (row.get("description") or "").replace("\n", " ")[:120]
        lines.append(
            f"- ID {row['id']}｜{row['name']}｜价格 ¥{row['price']}｜"
            f"库存 {row['num']}{row.get('unit') or '个'}｜描述：{description or '暂无'}"
        )
    return "\n".join(lines)


async def recommend_cake(
    query: RecommendationQuery | str | None = None,
    *,
    user_id: int | None = None,
    check_stock: bool | None = None,
) -> str:
    """Personalized cake recommendation.

    Pipeline:
      1) Compose search_text from structured query; pull top-20 candidates via
         search_products (text-relevance ranked, in_stock pre-filter).
      2) Apply max_price ceiling.
      3) Load UserProfile when user_id is given; add per-row personalization
         bonus to _relevance.
      4) Re-rank by combined score and take top 5.

    Anonymous users (user_id=None) and empty profiles degrade to pure text
    relevance, identical to the previous behavior.
    """
    if isinstance(query, str):
        query = RecommendationQuery(keywords=query)
    elif query is None:
        query = RecommendationQuery()
    if check_stock is not None:
        query = query.model_copy(update={"in_stock_only": check_stock})

    candidates, _ = await search_products(
        query.search_text(),
        limit=20,
        in_stock_only=query.in_stock_only,
    )

    if query.max_price is not None:
        candidates = [row for row in candidates if (row.get("price") or 0) <= query.max_price]

    profile = await _load_user_profile(user_id)
    for row in candidates:
        personal = _personalization_score(row, profile) if profile is not None else 0.0
        row["_score"] = row["_relevance"] + personal

    ranked = sorted(
        candidates,
        key=lambda row: (row["_score"], row["num"] > 0, -row["id"]),
        reverse=True,
    )[:5]

    if not ranked:
        return "当前商品库中没有可推荐的蛋糕。"

    lines = ["为您推荐以下蛋糕："]
    for index, row in enumerate(ranked, 1):
        stock_info = "有货" if row["num"] > 0 else "暂时售罄"
        description = (row.get("description") or "暂无").replace("\n", " ")
        lines.append(
            f"{index}. {row['name']} - ¥{row['price']}（{stock_info}，剩余{row['num']}{row.get('unit') or '个'}）\n"
            f"   {description}"
        )
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


__all__ = [
    "RecommendationQuery",
    "UserProfile",
    "check_stock",
    "get_product_facts",
    "recommend_cake",
    "search_products",
]
