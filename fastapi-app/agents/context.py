from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    """Trusted request context injected by LangGraph, hidden from the model schema."""

    user_id: int | None
    conversation_id: int | None
    user_message: str
