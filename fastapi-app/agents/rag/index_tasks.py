"""Outbox processing for synchronizing business data into the vector index."""

import asyncio
import logging

from models import Goods, IndexTask

from .vector_store import KnowledgeService, knowledge_service


logger = logging.getLogger(__name__)
INDEX_TASK_MAX_ATTEMPTS = 3


class IndexTaskService:
    def __init__(self, vector_store: KnowledgeService):
        self.vector_store = vector_store

    async def process(self, task_id: int) -> None:
        """Process one idempotent index task with a bounded retry count."""
        task = await IndexTask.get_or_none(id=task_id)
        if task is None or task.status == "done" or task.attempts >= INDEX_TASK_MAX_ATTEMPTS:
            return

        try:
            if task.entity_type == "goods" and task.action == "upsert":
                goods = await Goods.get_or_none(id=task.entity_id).prefetch_related("category")
                if goods is not None:
                    await asyncio.to_thread(self.vector_store.sync_goods, goods)
            elif task.entity_type == "goods" and task.action == "delete":
                await asyncio.to_thread(self.vector_store.remove_goods, task.entity_id)

            await IndexTask.filter(id=task.id).update(
                status="done",
                attempts=task.attempts + 1,
                last_error=None,
            )
        except Exception as exc:
            attempts = task.attempts + 1
            await IndexTask.filter(id=task.id).update(
                status="failed" if attempts >= INDEX_TASK_MAX_ATTEMPTS else "pending",
                attempts=attempts,
                last_error=str(exc)[:500],
            )
            logger.warning(
                "index task %s failed (attempt %d/%d): %s",
                task_id,
                attempts,
                INDEX_TASK_MAX_ATTEMPTS,
                exc,
            )
            raise

    async def run_pending(self, limit: int = 100) -> dict:
        """Retry pending and failed tasks, returning batch statistics."""
        tasks = await IndexTask.filter(status__in=["pending", "failed"]).order_by("id").limit(limit)
        succeeded = 0
        failed = 0
        for task in tasks:
            try:
                await self.process(task.id)
                succeeded += 1
            except Exception:
                failed += 1
        return {"processed": len(tasks), "succeeded": succeeded, "failed": failed}

    async def stats(self) -> dict:
        return {
            "pending": await IndexTask.filter(status="pending").count(),
            "failed": await IndexTask.filter(status="failed").count(),
            "done": await IndexTask.filter(status="done").count(),
        }


index_task_service = IndexTaskService(knowledge_service)
