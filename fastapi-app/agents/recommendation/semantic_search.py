"""语义搜索：复用客服链路已维护的 goods_base 商品向量索引。

同一份商品向量，客服 Agent 在用、搜索端也用——索引维护成本不变、能力翻倍。
排序 = 向量相似分 × 热度微调；事实（价格/库存）一律回查 MySQL，
向量库只负责"像不像"，不承担"真不真"（与 Grounding 哲学一致）。

三级兜底：向量语义 → 关键字 LIKE → 热销商品，保证任何查询都有可行动的结果。"""
import asyncio
import logging
import math

from tortoise.expressions import Q
from tortoise.functions import Count

from agents.rag import knowledge_service
from models import Goods, Orders
from settings import SEMANTIC_SEARCH_CONFIG

logger = logging.getLogger(__name__)

# 与 api.orders / agents.tools.order 保持一致的口径；agents 层不依赖 api 层
ORDER_CANCELLED = "已取消"


async def _vector_candidates(query: str, top_k: int) -> list:
    """向量检索候选。同步 Embedding 调用放线程池，不阻塞事件循环。"""
    return await asyncio.to_thread(
        knowledge_service.search_goods_with_ids, query, top_k
    )


async def sales_map() -> dict:
    """各商品有效销量（排除已取消订单）。

    计划文档假设存在 goods.sales_volume 字段，实际并不存在——
    从 orders 聚合得出的销量是同一信号且天然排除取消，比冗余列更可信。"""
    rows = await (
        Orders.exclude(status=ORDER_CANCELLED)
        .annotate(cnt=Count("id"))
        .group_by("goods_id")
        .values("goods_id", "cnt")
    )
    return {row["goods_id"]: row["cnt"] for row in rows}


def _goods_dict(goods) -> dict:
    return {
        "id": goods.id,
        "name": goods.name,
        "img": goods.img,
        "price": goods.price,
        "unit": goods.unit,
        "num": goods.num,
        "description": goods.description,
        "categoryId": goods.category_id,
        "categoryName": goods.category.name if goods.category else None,
    }


async def search(query: str, top_k: int = None) -> dict:
    """三级兜底搜索，返回 {mode: semantic|keyword|hot, list, query}。"""
    top_k = top_k or SEMANTIC_SEARCH_CONFIG["default_top_k"]
    q = (query or "").strip()
    if not q:
        return {"mode": "hot", "query": q, "list": await _hot_fallback(top_k)}

    heat_weight = SEMANTIC_SEARCH_CONFIG["heat_weight"]
    candidates = []
    try:
        candidates = await _vector_candidates(
            q, SEMANTIC_SEARCH_CONFIG["candidate_k"]
        )
    except Exception:
        # Embedding/向量库不可用不应导致搜索 404：静默降级到关键字
        logger.warning("semantic vector search failed, fallback to keyword", exc_info=True)

    items = []
    if candidates:
        ids = [c["goods_id"] for c in candidates]
        # 实时库存过滤：向量库是异步派生索引，缺货/下架商品必须以 MySQL 为准
        rows = await Goods.filter(id__in=ids, num__gt=0).prefetch_related("category")
        row_map = {g.id: g for g in rows}
        sales = await sales_map()
        pops = {gid: math.log1p(sales.get(gid, 0)) for gid in row_map}
        max_pop = max(pops.values()) if pops else 0

        scored = []
        for c in candidates:
            goods = row_map.get(c["goods_id"])
            if goods is None:
                continue
            # distance 是 Chroma 的 L2 距离；越小越相似。归一化到 0~1 相似分。
            similarity = 1.0 / (1.0 + c["distance"])
            pop_norm = pops[goods.id] / max_pop if max_pop > 0 else 0.0
            score = similarity + heat_weight * pop_norm
            sold = sales.get(goods.id, 0)
            reason = f"语义匹配度 {similarity:.2f}"
            if sold > 0:
                reason += f" · 已售 {sold} 单"
            scored.append((score, reason, goods))

        scored.sort(key=lambda t: (-t[0], -t[2].id))
        items = [
            {**_goods_dict(goods), "reason": reason}
            for _, reason, goods in scored[:top_k]
        ]

    if items:
        return {"mode": "semantic", "query": q, "list": items}

    # 兜底一：关键字 LIKE（名称/描述），按销量排序
    rows = await (
        Goods.filter(Q(name__contains=q) | Q(description__contains=q), num__gt=0)
        .prefetch_related("category")
    )
    if rows:
        sales = await sales_map()
        rows = sorted(rows, key=lambda g: (-sales.get(g.id, 0), -g.id))
        return {
            "mode": "keyword",
            "query": q,
            "list": [
                {**_goods_dict(g), "reason": "按关键词匹配"}
                for g in rows[:top_k]
            ],
        }

    # 兜底二：热销商品 + 改写引导
    return {
        "mode": "hot",
        "query": q,
        "list": [
            {**_goods_dict(g), "reason": "热门推荐"}
            for g in await _hot_fallback(top_k)
        ],
    }


async def _hot_fallback(top_k: int) -> list:
    sales = await sales_map()
    rows = await Goods.filter(num__gt=0).prefetch_related("category")
    return sorted(rows, key=lambda g: (-sales.get(g.id, 0), -g.id))[:top_k]
