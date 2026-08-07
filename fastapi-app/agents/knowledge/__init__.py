"""Compatibility facade; new code imports from :mod:`agents.rag`."""

from agents.rag import IndexTaskService, KnowledgeService, index_task_service, knowledge_service

__all__ = ["IndexTaskService", "KnowledgeService", "index_task_service", "knowledge_service"]
