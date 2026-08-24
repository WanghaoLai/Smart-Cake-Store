"""用户钱包接口：余额、模拟充值和资金流水查询。"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from common.auth import get_current_customer
from common.exception_handler import ConflictException, CustomException
from common.pagination import clamp_page
from common.result import PageInfo, Result
from common.time import format_store_time
from models import User, WalletTransaction
from settings import WALLET_RECHARGE_MODE


router = APIRouter(prefix="/wallet", dependencies=[Depends(get_current_customer)])

PAYMENT_METHODS = {
    "alipay": "支付宝",
    "wechat": "微信支付",
    "bank_card": "银行卡",
}
MIN_RECHARGE = Decimal("1.00")
MAX_RECHARGE = Decimal("10000.00")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


class RechargeRequest(BaseModel):
    amount: Decimal
    payment_method: str
    request_id: str


def _money(value: Decimal) -> Decimal:
    try:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CustomException("充值金额格式不正确") from exc


def _summary(user: User) -> dict:
    return {
        "balance": user.balance,
        "currency": "CNY",
        "payment_methods": [
            {"value": value, "label": label} for value, label in PAYMENT_METHODS.items()
        ],
        # 当前项目没有接入第三方商户密钥，前端必须明确这是演示确认流程。
        "recharge_mode": WALLET_RECHARGE_MODE,
    }


@router.get("/summary")
async def summary(current_user: dict = Depends(get_current_customer)):
    user = await User.get(id=current_user["user_id"])
    return Result.success(_summary(user))


@router.post("/recharge")
async def recharge(data: RechargeRequest, current_user: dict = Depends(get_current_customer)):
    if WALLET_RECHARGE_MODE != "simulation":
        raise CustomException("充值服务尚未接入正式支付网关，请联系管理员")
    amount = _money(data.amount)
    method = (data.payment_method or "").strip()
    request_id = (data.request_id or "").strip()
    if amount < MIN_RECHARGE or amount > MAX_RECHARGE:
        raise CustomException(f"单次充值金额须在 {MIN_RECHARGE:.2f} 至 {MAX_RECHARGE:.2f} 元之间")
    if method not in PAYMENT_METHODS:
        raise CustomException("不支持的支付方式")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise CustomException("充值请求标识格式不正确")

    try:
        async with in_transaction():
            user = await User.filter(id=current_user["user_id"]).select_for_update().first()
            user.balance = _money(user.balance + amount)
            await user.save(update_fields=["balance"])
            await WalletTransaction.create(
                user_id=user.id,
                type="recharge",
                amount=amount,
                balance_after=user.balance,
                payment_method=method,
                status="success",
                request_id=request_id,
                remark=f"{PAYMENT_METHODS[method]}充值（演示）",
            )
    except IntegrityError:
        # 客户端超时重试时保持幂等；同一 request_id 不会重复入账。
        existing = await WalletTransaction.get_or_none(request_id=request_id)
        if existing and existing.user_id == current_user["user_id"] and existing.type == "recharge":
            user = await User.get(id=current_user["user_id"])
            return Result.success(_summary(user))
        raise ConflictException("充值请求已被使用，请重新发起")

    return Result.success(_summary(user))


@router.get("/transactions")
async def transactions(
    type: str = "",
    pageNum: int = 1,
    pageSize: int = 10,
    current_user: dict = Depends(get_current_customer),
):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = WalletTransaction.filter(user_id=current_user["user_id"])
    if type:
        if type not in {"recharge", "payment", "refund"}:
            raise CustomException("交易类型不正确")
        query = query.filter(type=type)
    total = await query.count()
    rows = await query.order_by("-created_at", "-id").offset((pageNum - 1) * pageSize).limit(pageSize)
    labels = {"recharge": "充值", "payment": "订单支付", "refund": "订单退款"}
    data = [
        {
            "id": row.id,
            "type": row.type,
            "type_label": labels.get(row.type, row.type),
            "amount": row.amount,
            "balance_after": row.balance_after,
            "payment_method": row.payment_method,
            "order_id": row.order_id,
            "remark": row.remark,
            "created_at": format_store_time(row.created_at),
        }
        for row in rows
    ]
    return Result.success(PageInfo(total=total, list=data))
