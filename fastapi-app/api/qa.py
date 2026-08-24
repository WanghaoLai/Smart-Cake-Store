"""Product-detail AI Q&A HTTP API."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agents.product_qa import (
    deterministic_answer,
    generate_ai_answer,
    grounded_fallback,
    load_product_facts,
)
from common.auth import get_current_user
from common.exception_handler import CustomException, NotFoundException
from common.rate_limit import SlidingWindowRateLimiter
from common.result import Result
from settings import GOODS_QA_RATE_LIMIT, GOODS_QA_RATE_WINDOW_SECONDS


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", dependencies=[Depends(get_current_user)])
qa_rate_limiter = SlidingWindowRateLimiter(GOODS_QA_RATE_LIMIT, GOODS_QA_RATE_WINDOW_SECONDS)


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in {"user", "assistant"}:
            raise ValueError("role 仅支持 user/assistant")
        return value


class GoodsQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goods_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=500)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=6)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("问题不能为空")
        return value


@router.post("/goods")
async def ask_goods(data: GoodsQuestion, current_user: dict = Depends(get_current_user)):
    limiter_key = f"{current_user['role']}:{current_user['user_id']}"
    if not qa_rate_limiter.allow(limiter_key):
        raise CustomException(
            f"提问过于频繁，每 {GOODS_QA_RATE_WINDOW_SECONDS} 秒最多 {GOODS_QA_RATE_LIMIT} 次，请稍后再试",
            status_code=429,
        )
    facts = await load_product_facts(data.goods_id)
    if facts is None:
        raise NotFoundException("商品不存在或已下架")

    direct = deterministic_answer(data.question, facts)
    if direct is not None:
        return Result.success({"answer": direct, "source": "database"})

    history = [item.model_dump() for item in data.history]
    try:
        answer = await generate_ai_answer(data.question, history, facts)
    except Exception as exc:
        logger.warning("goods qa model unavailable goods_id=%s user_id=%s error=%s", data.goods_id, current_user["user_id"], exc)
        answer = None
    if answer:
        return Result.success({"answer": answer, "source": "ai_grounded"})
    return Result.success({"answer": grounded_fallback(facts), "source": "database_fallback"})
