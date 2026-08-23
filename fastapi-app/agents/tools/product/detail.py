"""Product answers are rendered exclusively from current MySQL rows."""

import json
import re
from collections.abc import Iterable
from decimal import Decimal

from models import Goods

from .search import search_products


def extract_product_ids(model_answer: str, limit: int = 10) -> list[int]:
    """Read only a structured ``product_ids`` field from model output."""
    candidates = re.findall(r"\{[^{}]*\"product_ids\"[^{}]*\}", model_answer, re.DOTALL)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        values = payload.get("product_ids")
        if not isinstance(values, list):
            continue
        result: list[int] = []
        for value in values:
            if isinstance(value, bool):
                continue
            try:
                product_id = int(value)
            except (TypeError, ValueError):
                continue
            if product_id > 0 and product_id not in result:
                result.append(product_id)
            if len(result) >= limit:
                break
        return result
    return []


async def _rows_by_ids(product_ids: Iterable[int]) -> list[dict]:
    ordered_ids = list(dict.fromkeys(product_ids))[:10]
    if not ordered_ids:
        return []
    rows = await Goods.filter(id__in=ordered_ids).values(
        "id", "name", "price", "num", "unit", "description",
    )
    by_id = {row["id"]: row for row in rows}
    return [by_id[product_id] for product_id in ordered_ids if product_id in by_id]


def _render(rows: list[dict]) -> str:
    if not rows:
        return "当前商品库中没有可推荐的蛋糕。"
    lines = ["根据当前商品库，为您找到以下蛋糕："]
    for index, row in enumerate(rows, 1):
        description = (row.get("description") or "").replace("\n", " ")[:120]
        price = Decimal(str(row["price"])).quantize(Decimal("0.01"))
        lines.append(
            f"{index}. **{row['name']}** — ¥{price}"
            f"（库存 {row['num']}{row.get('unit') or '个'}）\n   {description}"
        )
    return "\n".join(lines)


async def build_verified_product_answer(
    query: str,
    limit: int = 3,
    product_ids: Iterable[int] | None = None,
) -> str:
    """Resolve selectors, then render every catalog fact from MySQL."""
    rows = await _rows_by_ids(product_ids or [])
    if not rows:
        rows, _ = await search_products(query, limit)
    return _render(rows)


async def rebuild_product_answer(model_answer: str, query: str, limit: int = 3) -> str:
    """Discard model catalog prose and retain only verified ID choices."""
    return await build_verified_product_answer(
        query,
        limit=limit,
        product_ids=extract_product_ids(model_answer, limit=limit),
    )


__all__ = ["build_verified_product_answer", "extract_product_ids", "rebuild_product_answer"]
