from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(TypedDict, total=False):
    """Minimal state contract for the future explicit LangGraph workflow."""

    messages: Annotated[list, add_messages]
    intent: str
    plan: list[str]
    tool_results: list[dict]
    verified: bool
    response: str


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    history: list[ChatMessage] = Field(default_factory=list)


class AgentResponse(BaseModel):
    content: str


__all__ = ["AgentRequest", "AgentResponse", "AgentState", "ChatMessage"]
