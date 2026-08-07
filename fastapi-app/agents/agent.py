"""Public application facade for the customer-service agent.

The class in this module is intentionally independent of a concrete graph
implementation.  Today it executes LangChain's compiled graph; a native
LangGraph graph can replace it later without changing the HTTP layer.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agents.context import AgentContext
from agents.memory.checkpointer import ConversationMemory
from agents.rag.retriever import format_grounding_message
from agents.config import AgentProfile
from agents.tools import business_repository


logger = logging.getLogger(__name__)


class AgentUnavailableError(RuntimeError):
    """Raised when the Agent cannot safely produce a user response."""


def _message_text(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content.strip()
    parts = []
    for block in message.content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
            parts.append(str(block.get("text", "")))
    return "".join(parts).strip()


def _truncate(value: Any, limit: int = 40) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "..."


def _summarize_tool_chain(messages: list[BaseMessage]) -> list[dict]:
    """Walk LangGraph output messages and pair each AIMessage.tool_calls with
    its ToolMessage result. Returns a list of dicts in execution order:

        {"tool": str, "args": {k: truncated_str}, "ok": bool|None, "result_chars": int|None}

    Used for post-hoc debugging and tool-selection audits. Args are truncated
    so user message fragments don't land in the log verbatim.
    """
    chain: list[dict] = []
    pending: dict[str, dict] = {}  # tool_call_id → entry awaiting its result
    for msg in messages:
        if isinstance(msg, AIMessage):
            for call in getattr(msg, "tool_calls", None) or []:
                entry = {
                    "tool": call.get("name", "?"),
                    "args": {k: _truncate(v) for k, v in (call.get("args") or {}).items()},
                    "ok": None,
                    "result_chars": None,
                }
                chain.append(entry)
                call_id = call.get("id")
                if call_id:
                    pending[call_id] = entry
        elif isinstance(msg, ToolMessage):
            entry = pending.pop(msg.tool_call_id, None)
            if entry is None:
                continue
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            entry["ok"] = getattr(msg, "status", "") != "error"
            entry["result_chars"] = len(content)
    return chain


class LangChainAgentExecutor:
    def __init__(
        self,
        profile: AgentProfile,
        graph: Any,
        tools: list,
        configured: bool = True,
        grounding_service: Any | None = None,
    ):
        self.profile = profile
        self.graph = graph
        self.tools = tools
        self.configured = configured
        self.memory = ConversationMemory(profile.max_history)
        self.grounding_service = grounding_service

    async def process_message(
        self,
        user_message: str,
        history: list,
        user_id: int | None = None,
        conversation_id: int | None = None,
    ) -> str:
        if not self.configured:
            raise AgentUnavailableError("智能客服尚未配置模型凭据")

        messages = self.memory.build(history, user_message)
        grounding_sources: list[str] = []
        if self.grounding_service is not None:
            evidence = await self.grounding_service.collect(user_message, user_id, history)
            if evidence:
                grounding_sources = [item.source for item in evidence]
                # Keep retrieved content at user-message privilege rather than
                # promoting untrusted documents into the system prompt.
                messages.insert(-1, HumanMessage(content=format_grounding_message(evidence)))
        context = AgentContext(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
        )
        config = {
            "run_name": self.profile.name,
            "tags": ["cake-store", "customer-service"],
            "metadata": {
                "conversation_id": conversation_id,
                "grounding_sources": grounding_sources,
            },
            "recursion_limit": max(10, self.profile.max_model_calls * 3),
        }
        try:
            result = await self.graph.ainvoke(
                {"messages": messages},
                config=config,
                context=context,
            )
        except Exception as exc:
            logger.warning(
                "agent graph_failed conversation_id=%s user_id=%s grounding=%s error=%s",
                conversation_id, user_id, grounding_sources or "none", exc,
            )
            raise AgentUnavailableError("智能客服执行失败") from exc

        output_messages = result.get("messages", [])
        tool_chain = _summarize_tool_chain(output_messages)

        final_message = output_messages[-1] if output_messages else None
        if not isinstance(final_message, AIMessage):
            logger.warning(
                "agent invalid_final_message conversation_id=%s user_id=%s type=%s chain_len=%d",
                conversation_id, user_id, type(final_message).__name__ if final_message else "None",
                len(tool_chain),
            )
            raise AgentUnavailableError("智能客服未返回有效回答")
        answer = _message_text(final_message)
        if not answer:
            logger.warning(
                "agent empty_answer conversation_id=%s user_id=%s chain_len=%d",
                conversation_id, user_id, len(tool_chain),
            )
            raise AgentUnavailableError("智能客服返回了空回答")

        # Single INFO line per request — easy to grep & aggregate. The chain
        # detail goes to DEBUG to keep prod logs at one line per request.
        chain_names = " -> ".join(item["tool"] for item in tool_chain) or "none"
        logger.info(
            "agent tool_chain conversation_id=%s user_id=%s grounding=%s chain_len=%d chain=%s answer_chars=%d",
            conversation_id, user_id, ",".join(grounding_sources) or "none",
            len(tool_chain), chain_names, len(answer),
        )
        if tool_chain:
            logger.debug(
                "agent tool_chain_detail conversation_id=%s detail=%s",
                conversation_id,
                tool_chain,
            )

        if "MySQL实时商品" in grounding_sources:
            try:
                if not await business_repository.validate_product_answer(answer):
                    logger.info(
                        "agent answer_rebuilt conversation_id=%s user_id=%s reason=mysql_validation_failed",
                        conversation_id, user_id,
                    )
                    answer = await business_repository.build_verified_product_answer(
                        "\n".join([
                            *[
                                str(item.get("content", ""))
                                for item in history[-6:]
                                if item.get("role") == "user"
                            ],
                            user_message,
                        ])
                    )
            except Exception as exc:
                logger.warning(
                    "agent rebuild_failed conversation_id=%s user_id=%s error=%s",
                    conversation_id, user_id, exc,
                )
                raise AgentUnavailableError("商品信息校验失败") from exc
        return answer

    async def process_message_stream(
        self,
        user_message: str,
        history: list,
        user_id: int | None = None,
        conversation_id: int | None = None,
    ) -> AsyncIterator[str]:
        # Tool calls and tool results are deliberately completed server-side before
        # output. This prevents internal calls from leaking through the public SSE.
        answer = await self.process_message(user_message, history, user_id, conversation_id)
        for index in range(0, len(answer), 24):
            yield answer[index:index + 24]


# Compatibility for integrations that imported the former ``agents.agent``
# package.  These aliases contain no implementation; new code must use the
# responsibility-based modules above.
import sys as _sys
from agents.rag import retriever as grounding

executor = _sys.modules[__name__]
context = _sys.modules[AgentContext.__module__]
_sys.modules[f"{__name__}.executor"] = executor
_sys.modules[f"{__name__}.context"] = context
_sys.modules[f"{__name__}.grounding"] = grounding

__all__ = ["AgentUnavailableError", "LangChainAgentExecutor"]
