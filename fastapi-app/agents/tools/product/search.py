"""Read-only product search, ranking, recommendation and stock queries."""
import re

from models import Goods


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
    """Small deterministic ranker used before the vector goods index is complete."""
    normalized_query = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]", "", query.lower())
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


async def search_products(query: str, limit: int = 8) -> tuple[list[dict], int]:
    rows = await Goods.all().limit(200).values(
        "id", "name", "price", "num", "unit", "description"
    )
    ranked = sorted(
        rows,
        key=lambda row: (
            _relevance(query, f"{row['name']} {row.get('description') or ''}"),
            row["num"] > 0,
            -row["id"],
        ),
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


async def recommend_cake(preference: str = "") -> str:
    if preference:
        goods_list = await Goods.filter(name__contains=preference).limit(5)
        if not goods_list:
            goods_list = await Goods.filter(description__contains=preference).limit(5)
    else:
        goods_list = await Goods.all().limit(5)

    if not goods_list:
        goods_list = await Goods.all().limit(5)

    lines = ["为您推荐以下蛋糕："]
    for i, g in enumerate(goods_list, 1):
        stock_info = "有货" if g.num > 0 else "暂时售罄"
        lines.append(f"{i}. {g.name} - ¥{g.price}（{stock_info}，剩余{g.num}{g.unit or '个'}）\n   {g.description}")
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


__all__ = ["check_stock", "get_product_facts", "recommend_cake", "search_products"]
