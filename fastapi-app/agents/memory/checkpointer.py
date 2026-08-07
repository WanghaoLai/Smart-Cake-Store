"""Convert persisted application messages into a bounded LangChain context."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agents.state import ChatMessage


class ConversationMemory:
    def __init__(self, max_messages: int):
        self.max_messages = max_messages

    def build(self, history: list[dict] | list[ChatMessage], user_message: str) -> list[BaseMessage]:
        normalized: list[BaseMessage] = []
        for raw in history:
            try:
                message = raw if isinstance(raw, ChatMessage) else ChatMessage.model_validate(raw)
            except Exception:
                continue
            content = message.content.strip()
            if not content:
                continue
            if message.role == "user":
                normalized.append(HumanMessage(content=content))
            elif message.role == "assistant":
                normalized.append(AIMessage(content=content))
        normalized = normalized[-self.max_messages:] if self.max_messages else []
        normalized.append(HumanMessage(content=user_message.strip()))
        return normalized
