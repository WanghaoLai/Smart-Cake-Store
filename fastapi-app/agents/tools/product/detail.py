"""Product answer verification and deterministic fallback rendering."""

import re

from models import Goods

from .search import search_products


async def validate_product_answer(answer: str) -> bool:
    """Reject catalog-style model output that names products absent from MySQL."""
    known_names = set(await Goods.all().values_list("name", flat=True))
    catalog_claim = any(marker in answer for marker in ("为您推荐", "推荐以下", "库存", "剩余", "¥", "￥"))
    if catalog_claim and not any(name in answer for name in known_names):
        return False

    priced_mentions = re.findall(
        r"(?:^|\n)\s*\d+[.、]\s*(?:\*\*)?([^*\n￥¥—–|｜]{2,40}?蛋糕)(?:\*\*)?\s*(?:[-—–|｜:]|\s)*[￥¥]",
        answer,
    )
    return all(mention.strip() in known_names for mention in priced_mentions)


async def build_verified_product_answer(query: str, limit: int = 3) -> str:
    """Build a model-independent fallback containing only current MySQL rows."""
    rows, _ = await search_products(query, limit)
    if not rows:
        return "当前商品库中没有可推荐的蛋糕。"
    lines = ["根据当前商品库，为您找到以下蛋糕："]
    for index, row in enumerate(rows, 1):
        description = (row.get("description") or "").replace("\n", " ")[:120]
        lines.append(
            f"{index}. **{row['name']}** — ¥{row['price']}"
            f"（库存 {row['num']}{row.get('unit') or '个'}）\n   {description}"
        )
    return "\n".join(lines)


__all__ = ["build_verified_product_answer", "validate_product_answer"]
