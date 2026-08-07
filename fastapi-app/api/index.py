"""Administrative vector-index operations.

The historical ``/chat`` URL prefix is retained for frontend/API compatibility;
index lifecycle concerns no longer live in the conversation endpoint module.
"""

import asyncio

from fastapi import APIRouter, Depends

from agents.rag import index_task_service, knowledge_service
from common.auth import get_current_admin, get_current_user
from common.result import Result
from models import Goods


router = APIRouter(prefix="/chat", dependencies=[Depends(get_current_user)])


@router.post("/rebuild-index", dependencies=[Depends(get_current_admin)])
async def rebuild_index():
    """Rebuild the derived goods vector index and return its statistics."""
    goods_list = await Goods.all().prefetch_related("category")
    await asyncio.to_thread(knowledge_service.sync_all_goods, goods_list)
    stats = await asyncio.to_thread(knowledge_service.get_stats)
    return Result.success(stats)


@router.post("/index/run-pending", dependencies=[Depends(get_current_admin)])
async def run_pending_index_tasks():
    """Retry pending/failed outbox index tasks."""
    return Result.success(await index_task_service.run_pending(limit=100))


@router.get("/index/stats", dependencies=[Depends(get_current_admin)])
async def index_stats():
    """Return outbox counts and expose MySQL/ChromaDB index drift."""
    outbox = await index_task_service.stats()
    vector = await asyncio.to_thread(knowledge_service.get_stats)
    mysql_goods = await Goods.all().count()
    return Result.success({
        "outbox": outbox,
        "vector": vector,
        "mysql_goods": mysql_goods,
        "goods_index_healthy": vector["goods_count"] == mysql_goods,
        "missing_goods_vectors": max(mysql_goods - vector["goods_count"], 0),
    })
