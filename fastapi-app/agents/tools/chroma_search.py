"""Backward-compatible import for the knowledge-search tool."""

from .knowledge import KnowledgeSearchArguments, create_chroma_search_tool

__all__ = ["KnowledgeSearchArguments", "create_chroma_search_tool"]
