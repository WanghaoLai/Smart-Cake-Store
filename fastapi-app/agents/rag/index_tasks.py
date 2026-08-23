"""Outbox processing for synchronizing business data into the vector index."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from models import Goods, IndexTask

from .vector_store import KnowledgeService, knowledge_service


logger = logging.getLogger(__name__)
INDEX_TASK_MAX_ATTEMPTS = 3
INDEX_TASK_LEASE_SECONDS = 300


class IndexTaskService:
    def __init__(self, vector_store: KnowledgeService):
        self.vector_store = vector_store

    async def process(self, task_id: int) -> bool:
        """Atomically claim and process one task; return whether this worker claimed it."""
        claim_token = str(uuid.uuid4())
        claimed = await IndexTask.filter(
            id=task_id,
            status__in=["pending", "failed"],
            attempts__lt=INDEX_TASK_MAX_ATTEMPTS,
        ).update(
            status="processing",
            claim_token=claim_token,
            processing_started_at=datetime.now(timezone.utc),
        )
        if claimed != 1:
            return False
        task = await IndexTask.get(id=task_id)

        try:
            if task.entity_type == "goods" and task.action == "upsert":
                goods = await Goods.get_or_none(id=task.entity_id).prefetch_related("category")
                if goods is not None:
                    await asyncio.to_thread(self.vector_store.sync_goods, goods)
            elif task.entity_type == "goods" and task.action == "delete":
                await asyncio.to_thread(self.vector_store.remove_goods, task.entity_id)

            await IndexTask.filter(
                id=task.id, status="processing", claim_token=claim_token,
            ).update(
                status="done",
                attempts=task.attempts + 1,
                last_error=None,
                claim_token=None,
                processing_started_at=None,
            )
        except Exception as exc:
            attempts = task.attempts + 1
            await IndexTask.filter(
                id=task.id, status="processing", claim_token=claim_token,
            ).update(
                status="failed" if attempts >= INDEX_TASK_MAX_ATTEMPTS else "pending",
                attempts=attempts,
                last_error=str(exc)[:500],
                claim_token=None,
                processing_started_at=None,
            )
            logger.warning(
                "index task %s failed (attempt %d/%d): %s",
                task_id,
                attempts,
                INDEX_TASK_MAX_ATTEMPTS,
                exc,
            )
            raise
        return True

    async def run_pending(self, limit: int = 100) -> dict:
        """Retry pending and failed tasks, returning batch statistics."""
        lease_cutoff = datetime.now(timezone.utc) - timedelta(seconds=INDEX_TASK_LEASE_SECONDS)
        recovered = await IndexTask.filter(
            status="processing", processing_started_at__lt=lease_cutoff,
        ).update(
            status="pending",
            claim_token=None,
            processing_started_at=None,
            last_error="任务租约超时，已重新排队",
        )
        tasks = await IndexTask.filter(status__in=["pending", "failed"]).order_by("id").limit(limit)
        succeeded = 0
        failed = 0
        claimed = 0
        for task in tasks:
            try:
                if await self.process(task.id):
                    claimed += 1
                    succeeded += 1
            except Exception:
                claimed += 1
                failed += 1
        return {"processed": claimed, "succeeded": succeeded, "failed": failed, "recovered": recovered}

    async def stats(self) -> dict:
        return {
            "pending": await IndexTask.filter(status="pending").count(),
            "failed": await IndexTask.filter(status="failed").count(),
            "processing": await IndexTask.filter(status="processing").count(),
            "done": await IndexTask.filter(status="done").count(),
        }


index_task_service = IndexTaskService(knowledge_service)
