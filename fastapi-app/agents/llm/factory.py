"""LLM construction boundary.

Provider-specific details stay here so graph assembly and business logic only
depend on a chat-model interface.
"""

from langchain_openai import ChatOpenAI

from agents.config import AgentSettings


def create_dashscope_model(settings: AgentSettings) -> ChatOpenAI:
    return ChatOpenAI(
        # Keep non-AI routes bootable in environments that have not provisioned
        # the secret yet. The executor rejects chat requests before network I/O.
        api_key=settings.api_key or "not-configured",
        base_url=settings.base_url,
        model=settings.model,
        temperature=settings.temperature,
        timeout=settings.timeout_seconds,
        # Retry policy is owned by LangChain middleware to keep one retry layer.
        max_retries=0,
        streaming=False,
        model_kwargs={"parallel_tool_calls": False},
    )
