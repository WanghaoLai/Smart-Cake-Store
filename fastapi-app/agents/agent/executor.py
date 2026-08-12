"""Stable application facade over the LangChain Agent runtime."""

import logging
from collections.abc import AsyncIterator
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agents.config import AgentProfile
from agents.tools.product import build_verified_product_answer, validate_product_answer

from .harness import AgentComponents, AgentContext
from .grounding import format_grounding_message


logger = logging.getLogger(__name__)


class AgentRuntime(Protocol):
    """Minimal LangChain runtime surface required by the application layer."""

    async def ainvoke(
        self,
        input_data: dict,
        config: dict | None = None,
        *,
        context: AgentContext | None = None,
    ) -> dict: ...


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
    """Pair model tool calls with results for bounded operational logging."""
    chain: list[dict] = []
    pending: dict[str, dict] = {}
    for message in messages:
        if isinstance(message, AIMessage):
            for call in getattr(message, "tool_calls", None) or []:
                entry = {
                    "tool": call.get("name", "?"),
                    "args": {key: _truncate(value) for key, value in (call.get("args") or {}).items()},
                    "ok": None,
                    "result_chars": None,
                }
                chain.append(entry)
                if call.get("id"):
                    pending[call["id"]] = entry
        elif isinstance(message, ToolMessage):
            entry = pending.pop(message.tool_call_id, None)
            if entry is None:
                continue
            content = message.content if isinstance(message.content, str) else str(message.content)
            entry["ok"] = getattr(message, "status", "") != "error"
            entry["result_chars"] = len(content)
    return chain


class CustomerServiceAgent:
    """Application-level Agent used by HTTP endpoints.

    LangChain owns the model/tool loop. This facade owns application concerns:
    persisted history adaptation, trusted context, deterministic grounding,
    error isolation, observability, and final-answer validation.
    """

    framework = "langchain"

    def __init__(
        self,
        profile: AgentProfile,
        runtime: AgentRuntime,
        components: AgentComponents,
        configured: bool = True,
    ):
        configured_tools = [tool.name for tool in components.harness.tools]
        if configured_tools != profile.tools:
            raise ValueError("Agent 组件工具顺序必须与配置白名单一致")
        self.profile = profile
        self.runtime = runtime
        self.components = components
        self.configured = configured

    @property
    def tools(self) -> list:
        """Compatibility view for integrations inspecting enabled tools."""
        return list(self.components.harness.tools)

    async def process_message(
        self,
        user_message: str,
        history: list,
        user_id: int | None = None,
        conversation_id: int | None = None,
    ) -> str:
        if not self.configured:
            raise AgentUnavailableError("智能客服尚未配置模型凭据")

        harness = self.components.harness
        messages = harness.memory.build(history, user_message)
        grounding_sources: list[str] = []
        evidence = await harness.grounding.collect(user_message, user_id, history)
        if evidence:
            grounding_sources = [item.source for item in evidence]
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
            result = await self.runtime.ainvoke(
                {"messages": messages},
                config=config,
                context=context,
            )
        except Exception as exc:
            logger.warning(
                "agent runtime_failed conversation_id=%s user_id=%s grounding=%s error=%s",
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

        chain_names = " -> ".join(item["tool"] for item in tool_chain) or "none"
        logger.info(
            "agent tool_chain conversation_id=%s user_id=%s grounding=%s chain_len=%d chain=%s answer_chars=%d",
            conversation_id, user_id, ",".join(grounding_sources) or "none",
            len(tool_chain), chain_names, len(answer),
        )
        if tool_chain:
            logger.debug("agent tool_chain_detail conversation_id=%s detail=%s", conversation_id, tool_chain)

        if "MySQL实时商品" in grounding_sources:
            try:
                if not await validate_product_answer(answer):
                    logger.info(
                        "agent answer_rebuilt conversation_id=%s user_id=%s reason=mysql_validation_failed",
                        conversation_id, user_id,
                    )
                    answer = await build_verified_product_answer(
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
        answer = await self.process_message(user_message, history, user_id, conversation_id)
        for index in range(0, len(answer), 24):
            yield answer[index:index + 24]


__all__ = [
    "AgentRuntime",
    "AgentUnavailableError",
    "CustomerServiceAgent",
]
