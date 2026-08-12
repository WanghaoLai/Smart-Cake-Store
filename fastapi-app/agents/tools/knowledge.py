"""LangChain retrieval tool backed by the existing ChromaDB knowledge service."""

import asyncio
import logging

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from agents.agent import AgentContext


logger = logging.getLogger(__name__)


class KnowledgeSearchArguments(BaseModel):
    query: str = Field(min_length=1, max_length=500, description="需要检索的问题或关键词")
    top_k: int | None = Field(default=None, ge=1, le=10, description="每个知识集合的结果数量")


def create_chroma_search_tool(knowledge_service, default_top_k: int = 3) -> BaseTool:
    @tool("search_knowledge", args_schema=KnowledgeSearchArguments)
    async def search_knowledge(
        query: str,
        top_k: int | None = None,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """检索店铺政策、商品描述和商品语义索引；回答非实时知识问题时使用。"""
        try:
            results = await asyncio.to_thread(
                knowledge_service.search,
                query,
                top_k or default_top_k,
            )
        except Exception:
            logger.exception("search_knowledge tool failed")
            return "知识库暂时不可用，请基于其他可靠信息回答或建议用户稍后重试。"
        if not results:
            return "知识库中没有找到相关信息。"
        return "\n".join(
            f"- [{item.get('source', 'unknown')}] {item.get('content', '')}" for item in results
        )

    return search_knowledge
