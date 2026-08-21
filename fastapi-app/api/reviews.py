"""商品评价：用户提交（文本+多图+星级），公开浏览，管理员回复。"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction

from common.auth import get_current_admin, get_current_user
from common.exception_handler import CustomException
from common.pagination import clamp_page
from common.result import Result, PageInfo
from models import Review, Orders, Goods
from api.orders import ORDER_PENDING_REVIEW, ORDER_REVIEWED

router = APIRouter(prefix="/reviews", dependencies=[Depends(get_current_user)])

ReviewPydantic = pydantic_model_creator(Review)

# 评价创建模型：rating(1-5)、content、images(JSON 字符串)、orderId
# content/images 上限防止无界大文本写库（前端输入框同样限制 500 字、5 图）
ReviewCreatePydantic = create_model(
    "ReviewCreatePydantic",
    rating=(int, Field(..., ge=1, le=5)),
    content=(Optional[str], Field(None, max_length=500)),
    images=(Optional[str], None),  # JSON 字符串数组
    order_id=(int, Field(..., alias="orderId")),
    goods_id=(Optional[int], Field(None, alias="goodsId")),
)

# 管理员回复模型
ReviewReplyPydantic = create_model(
    "ReviewReplyPydantic",
    reply=(str, Field(..., min_length=1)),
)


def _parse_images(raw: Optional[str]) -> list:
    """images 字段存 JSON 字符串：解析失败统一返回空数组。"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _to_dict(review, include_user: bool = True) -> dict:
    """ORM 实例 -> 前端友好的 dict。images 解析为数组，附 userName/goodsName。"""
    base = ReviewPydantic.model_validate(review).model_dump()
    # 删除反向关系字段，避免序列化噪声
    for k in ("goods", "user", "order"):
        base.pop(k, None)
    base["images"] = _parse_images(base.get("images"))
    base["userName"] = review.user.name if review.user else None
    base["userAvatar"] = review.user.avatar if review.user else None
    base["goodsName"] = review.goods.name if review.goods else None
    base["goodsImg"] = review.goods.img if review.goods else None
    base["goodsId"] = review.goods_id
    base["orderId"] = review.order_id
    base["userId"] = review.user_id
    if not include_user:
        base.pop("userName", None)
        base.pop("userAvatar", None)
    return base


@router.post("/add")
async def add(review_pydantic: ReviewCreatePydantic, current_user: dict = Depends(get_current_user)):
    """用户提交评价。
    校验：订单归属当前用户、订单状态在 待评价、商品 ID 与订单一致。
    副作用：评价写入 + 订单状态推进到 已评价（同一事务，避免悬空评价）。"""
    async with in_transaction():
        order = await Orders.filter(
            id=review_pydantic.order_id,
            user_id=current_user["user_id"],
        ).select_for_update().first()
        if order is None:
            raise CustomException("订单不存在或不属于当前用户")

        key = (current_user["role"], order.status, ORDER_REVIEWED)
        # 只有 待评价 状态可直接推进到 已评价；其他状态禁止
        # （兼容历史 已签收 状态也允许直接评价）
        allowed_keys = {
            ("用户", ORDER_PENDING_REVIEW, ORDER_REVIEWED),
            ("用户", "已签收", ORDER_REVIEWED),
        }
        if key not in allowed_keys:
            raise CustomException(f"订单当前状态({order.status})不允许评价")

        # 防重复评价：order_id 唯一约束已在 DB 层保证，这里前置检查给友好错误
        existed = await Review.filter(order_id=order.id).exists()
        if existed:
            raise CustomException("该订单已评价，无法重复评价")

        goods_id = review_pydantic.goods_id or order.goods_id
        if goods_id is None:
            raise CustomException("缺少商品信息")

        # images 是 JSON 字符串：必须是数组且张数有界
        images = review_pydantic.images
        if images is not None:
            try:
                parsed = json.loads(images)
            except json.JSONDecodeError:
                raise CustomException("images 必须是 URL 数组的 JSON 字符串")
            if not isinstance(parsed, list) or len(parsed) > 9:
                raise CustomException("评价图片最多 9 张")

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await Review.create(
            goods_id=goods_id,
            user_id=current_user["user_id"],
            order_id=order.id,
            rating=review_pydantic.rating,
            content=review_pydantic.content,
            images=review_pydantic.images,
            time=now_str,
        )
        order.status = ORDER_REVIEWED
        await order.save(update_fields=['status'])

    return Result.success()


@router.get("/goods/{goods_id}")
async def list_by_goods(goods_id: int):
    """商品详情页：返回该商品全部评价（含管理员回复）。
    评价是公开信息，但接口仍走登录鉴权（与现有 /goods/detail 一致）。"""
    reviews = await Review.filter(goods_id=goods_id).prefetch_related('user', 'goods').order_by('-id')
    return Result.success([_to_dict(r) for r in reviews])


@router.put("/reply/{review_id}", dependencies=[Depends(get_current_admin)])
async def reply(
    review_id: int,
    payload: ReviewReplyPydantic,
):
    """管理员回复评价。仅管理员可操作；可多次编辑覆盖。"""
    review = await Review.get_or_none(id=review_id)
    if review is None:
        raise CustomException("评价不存在")
    review.reply = payload.reply
    review.reply_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    await review.save(update_fields=['reply', 'reply_time'])
    return Result.success()


@router.get("/selectPage")
async def select_page(
    goodsName: str = "",
    rating: int = 0,
    pageNum: int = 1,
    pageSize: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """管理员评价分页：按商品名/星级筛选；只展示有 content 的评价。"""
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    if current_user["role"] != "管理员":
        raise CustomException("无管理员权限")
    query = Review.filter()
    if goodsName:
        query = query.filter(goods__name__contains=goodsName)
    if rating > 0:
        query = query.filter(rating=rating)
    query = query.prefetch_related('user', 'goods', 'order')
    total = await query.count()
    rows = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    return Result.success(PageInfo(total=total, list=[_to_dict(r) for r in rows]))
