"""Model component for the LangChain application Agent."""

from langchain_openai import ChatOpenAI

from agents.config import AgentSettings


def create_model(settings: AgentSettings) -> ChatOpenAI:
    """Create the configured OpenAI-compatible DashScope chat model."""
    return ChatOpenAI(
        api_key=settings.api_key or "not-configured",
        base_url=settings.base_url,
        model=settings.model,
        temperature=settings.temperature,
        timeout=settings.timeout_seconds,
        # LangChain middleware owns retries so there is only one retry layer.
        max_retries=0,
        streaming=False,
        model_kwargs={"parallel_tool_calls": False},
    )


__all__ = ["create_model"]
