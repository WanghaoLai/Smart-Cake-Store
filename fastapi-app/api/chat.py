import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.agent import AgentUnavailableError
from agents.factory import create_customer_service_agent
from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result
from models import Conversation, Message


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", dependencies=[Depends(get_current_user)])

customer_service_agent = create_customer_service_agent()


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="新对话", max_length=255)


class MessageRequest(BaseModel):
    conversation_id: int
    message: str = Field(min_length=1, max_length=10000)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/conversation")
async def create_conversation(data: ConversationCreate, current_user: dict = Depends(get_current_user)):
    conversation = await Conversation.create(
        user_id=current_user["user_id"],
        title=data.title
    )
    return Result.success({"id": conversation.id, "title": conversation.title})


@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    conversations = await Conversation.filter(user_id=current_user["user_id"]).order_by("-updated_at")
    result = []
    for conv in conversations:
        result.append({
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": conv.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return Result.success(result)


async def _check_conversation_owner(conversation_id: int, current_user: dict) -> Conversation:
    """校验会话归属：本人或管理员可访问，否则抛异常。"""
    conversation = await Conversation.get_or_none(id=conversation_id)
    if conversation is None:
        raise CustomException("会话不存在")
    if current_user["role"] != "管理员" and conversation.user_id != current_user["user_id"]:
        raise CustomException("无权访问该会话")
    return conversation


@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: int, current_user: dict = Depends(get_current_user)):
    await _check_conversation_owner(conversation_id, current_user)
    messages = await Message.filter(conversation_id=conversation_id).order_by("created_at")
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return Result.success(result)


@router.post("/send")
async def send_message(data: MessageRequest, current_user: dict = Depends(get_current_user)):
    conversation = await _check_conversation_owner(data.conversation_id, current_user)

    await Message.create(
        conversation_id=data.conversation_id,
        role="user",
        content=data.message
    )

    history = await Message.filter(conversation_id=data.conversation_id).order_by("created_at")
    history_list = [{"role": msg.role, "content": msg.content} for msg in history]

    async def generate():
        yield _sse({"type": "status", "status": "thinking", "message": "正在思考并查询相关信息…"})
        try:
            full_response = await customer_service_agent.process_message(
                data.message,
                history_list[:-1],
                user_id=current_user["user_id"],
                conversation_id=data.conversation_id,
            )
        except AgentUnavailableError:
            logger.exception(
                "agent request failed: conversation_id=%s user_id=%s",
                data.conversation_id,
                current_user["user_id"],
            )
            full_response = "智能客服暂时不可用，请稍后重试或联系人工客服。"
            event_type = "error"
        else:
            event_type = "message"

        # Persist the complete result before emitting it so a disconnected browser
        # does not leave a user message without its corresponding assistant result.
        await Message.create(
            conversation_id=data.conversation_id,
            role="assistant",
            content=full_response,
        )
        if conversation.title == "新对话":
            title = data.message[:20] + "..." if len(data.message) > 20 else data.message
            await Conversation.filter(id=data.conversation_id).update(title=title)

        for index in range(0, len(full_response), 24):
            yield _sse({"type": event_type, "content": full_response[index:index + 24]})
        yield _sse({"type": "done", "done": True, "ok": event_type == "message"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: int, current_user: dict = Depends(get_current_user)):
    await _check_conversation_owner(conversation_id, current_user)
    await Message.filter(conversation_id=conversation_id).delete()
    await Conversation.filter(id=conversation_id).delete()
    return Result.success()
