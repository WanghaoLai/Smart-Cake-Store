import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.agent import AgentUnavailableError
from agents.factory import create_customer_service_agent
from common.auth import get_current_user
from common.exception_handler import CustomException, ForbiddenException, NotFoundException
from common.pagination import clamp_page
from common.rate_limit import SlidingWindowRateLimiter
from common.result import PageInfo, Result
from common.time import format_store_time
from models import Conversation, Message
from settings import CHAT_RATE_LIMIT, CHAT_RATE_WINDOW_SECONDS


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", dependencies=[Depends(get_current_user)])

customer_service_agent = create_customer_service_agent()

# 每用户独立窗口：User/Admin 主键可能重叠，必须角色 + ID 联合标识
send_rate_limiter = SlidingWindowRateLimiter(CHAT_RATE_LIMIT, CHAT_RATE_WINDOW_SECONDS)


class MessageRequest(BaseModel):
    conversation_id: int
    message: str = Field(min_length=1, max_length=10000)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/conversation")
async def create_conversation(
    current_user: dict = Depends(get_current_user),
):
    """Create a blank conversation without requiring a request payload."""
    conversation = await Conversation.create(
        user_id=current_user["user_id"],
        owner_role=current_user["role"],
        title="新对话",
    )
    return Result.success({"id": conversation.id, "title": conversation.title})


@router.get("/conversations")
async def get_conversations(
    pageNum: int = 1,
    pageSize: int = 20,
    current_user: dict = Depends(get_current_user),
):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = Conversation.filter(
        user_id=current_user["user_id"],
        owner_role=current_user["role"],
    ).order_by("-updated_at")
    total = await query.count()
    conversations = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    result = []
    for conv in conversations:
        result.append({
            "id": conv.id,
            "title": conv.title,
            "created_at": format_store_time(conv.created_at),
            "updated_at": format_store_time(conv.updated_at)
        })
    return Result.success(PageInfo(total=total, list=result))


async def _check_conversation_owner(conversation_id: int, current_user: dict) -> Conversation:
    """校验会话归属：本人或管理员可访问，否则抛异常。"""
    conversation = await Conversation.get_or_none(id=conversation_id)
    if conversation is None:
        raise NotFoundException("会话不存在")
    if (
        conversation.user_id != current_user["user_id"]
        or conversation.owner_role != current_user["role"]
    ):
        raise ForbiddenException("无权访问该会话")
    return conversation


@router.get("/messages/{conversation_id}")
async def get_messages(
    conversation_id: int,
    pageNum: int = 1,
    pageSize: int = 50,
    current_user: dict = Depends(get_current_user),
):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    await _check_conversation_owner(conversation_id, current_user)
    query = Message.filter(conversation_id=conversation_id)
    total = await query.count()
    messages = await query.order_by("-created_at", "-id").offset(
        (pageNum - 1) * pageSize
    ).limit(pageSize)
    messages.reverse()
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": format_store_time(msg.created_at)
        })
    return Result.success(PageInfo(total=total, list=result))


@router.post("/send")
async def send_message(data: MessageRequest, current_user: dict = Depends(get_current_user)):
    # 限流先于任何持久化与 LLM 调用：被拒的请求不留 Message 记录
    limiter_key = f"{current_user['role']}:{current_user['user_id']}"
    if not send_rate_limiter.allow(limiter_key):
        raise CustomException(
            f"发送过于频繁，每 {CHAT_RATE_WINDOW_SECONDS} 秒最多 {CHAT_RATE_LIMIT} 条，请稍后再试"
        )

    conversation = await _check_conversation_owner(data.conversation_id, current_user)

    await Message.create(
        conversation_id=data.conversation_id,
        role="user",
        content=data.message
    )

    history_limit = max(customer_service_agent.profile.max_history, 0) + 1
    history = await Message.filter(conversation_id=data.conversation_id).order_by(
        "-created_at", "-id"
    ).limit(history_limit)
    history.reverse()
    history_list = [{"role": msg.role, "content": msg.content} for msg in history]

    async def generate():
        yield _sse({"type": "status", "status": "thinking", "message": "正在思考并查询相关信息…"})
        usage = None
        try:
            invocation = await customer_service_agent.invoke(
                data.message,
                history_list[:-1],
                user_id=current_user["user_id"],
                conversation_id=data.conversation_id,
            )
            full_response = invocation.answer
            usage = invocation
            event_type = "message"
        except AgentUnavailableError:
            logger.exception(
                "agent request failed: conversation_id=%s user_id=%s",
                data.conversation_id,
                current_user["user_id"],
            )
            full_response = "智能客服暂时不可用，请稍后重试或联系人工客服。"
            event_type = "error"

        # Persist the complete result before emitting it so a disconnected browser
        # does not leave a user message without its corresponding assistant result.
        await Message.create(
            conversation_id=data.conversation_id,
            role="assistant",
            content=full_response,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            latency_ms=usage.latency_ms if usage else None,
            model=usage.model or None if usage else None,
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
