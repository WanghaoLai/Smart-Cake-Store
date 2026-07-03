import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from common.exception_handler import CustomException
from common.result import Result
from models import Conversation, Message, User, Goods
from services import LLMService, RAGService, ChatService
from settings import AI_CONFIG

router = APIRouter(prefix="/chat")

llm_service = LLMService(
    api_key=AI_CONFIG["dashscope_api_key"],
    model=AI_CONFIG["model"]
)
rag_service = RAGService(embedding_model=AI_CONFIG["embedding_model"])
chat_service = ChatService(llm_service, rag_service)


class ConversationCreate(BaseModel):
    title: Optional[str] = "新对话"


class MessageRequest(BaseModel):
    conversation_id: int
    message: str


@router.post("/conversation")
async def create_conversation(data: ConversationCreate, userId: int):
    conversation = await Conversation.create(
        user_id=userId,
        title=data.title
    )
    return Result.success({"id": conversation.id, "title": conversation.title})


@router.get("/conversations")
async def get_conversations(userId: int):
    conversations = await Conversation.filter(user_id=userId).order_by("-updated_at")
    result = []
    for conv in conversations:
        result.append({
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": conv.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return Result.success(result)


@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: int):
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
async def send_message(data: MessageRequest, userId: int):
    conversation = await Conversation.get_or_none(id=data.conversation_id)
    if not conversation:
        raise CustomException("会话不存在")

    await Message.create(
        conversation_id=data.conversation_id,
        role="user",
        content=data.message
    )

    history = await Message.filter(conversation_id=data.conversation_id).order_by("created_at")
    history_list = [{"role": msg.role, "content": msg.content} for msg in history]

    async def generate():
        full_response = ""
        async for chunk in chat_service.process_message_stream(data.message, history_list[:-1]):
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        await Message.create(
            conversation_id=data.conversation_id,
            role="assistant",
            content=full_response
        )

        if conversation.title == "新对话":
            title = data.message[:20] + "..." if len(data.message) > 20 else data.message
            await Conversation.filter(id=data.conversation_id).update(title=title)

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", # 禁用缓存
            "Connection": "keep-alive", # 保持连接
            "X-Accel-Buffering": "no" # 禁用 Nginx 代理缓冲
        }
    )


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: int):
    await Message.filter(conversation_id=conversation_id).delete()
    await Conversation.filter(id=conversation_id).delete()
    return Result.success()


@router.post("/rebuild-index")
async def rebuild_index():
    """重建 RAG 向量索引"""
    goods_list = await Goods.all().prefetch_related('category')
    rag_service.build_index(goods_list)
    return Result.success({"count": len(goods_list)})
