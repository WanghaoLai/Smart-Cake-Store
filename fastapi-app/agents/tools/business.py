"""LangChain tools for authenticated cake-store business operations."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, model_validator

from agents.agent import AgentContext
from agents.tools.order import cancel_order, get_order_status
from agents.tools.product import RecommendationQuery, check_stock, recommend_cake
from settings import APP_TIMEZONE


logger = logging.getLogger(__name__)

_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
_STORE_TIMEZONE = ZoneInfo(APP_TIMEZONE)


class OrderQuery(BaseModel):
    order_id: int | None = Field(default=None, gt=0, description="订单数据库 ID")
    order_no: str | None = Field(default=None, min_length=1, max_length=64, description="业务订单号")

    @model_validator(mode="after")
    def reject_ambiguous_identifier(self):
        if self.order_id is not None and self.order_no:
            raise ValueError("order_id 和 order_no 只能提供一个")
        return self


class CancelOrderArguments(OrderQuery):
    @model_validator(mode="after")
    def require_order_identifier(self):
        if self.order_id is None and not self.order_no:
            raise ValueError("必须提供 order_id 或 order_no")
        return self


_CANCEL_WORDS = ("取消", "撤销", "退订", "不要了", "cancel")
_CONFIRM_WORDS = ("确认", "确定", "是的", "好的", "可以", "同意", "yes")
_REJECT_CANCEL_PHRASES = ("不要取消", "不取消", "别取消", "暂不取消", "取消操作算了")


def _has_confirmed_cancel(context: AgentContext, order_id: int | None, order_no: str | None) -> bool:
    """Validate cancellation intent against trusted current input and recent dialogue."""
    current_message = context.user_message.strip().lower()
    if any(phrase in current_message for phrase in _REJECT_CANCEL_PHRASES):
        return False
    if any(word in current_message for word in _CANCEL_WORDS):
        return True
    if not any(word in current_message for word in _CONFIRM_WORDS):
        return False

    identifier = str(order_id if order_id is not None else order_no)
    for role, content in reversed(context.recent_history):
        if role != "assistant":
            continue
        normalized = content.lower()
        return (
            any(word in normalized for word in _CANCEL_WORDS)
            and identifier in normalized
            and any(word in normalized for word in ("确认", "确定", "是否", "要取消"))
        )
    return False


class RecommendationArguments(BaseModel):
    keywords: str = Field(default="", max_length=100, description="口味、原料、商品名关键词，如「草莓」「巧克力慕斯」")
    occasion: str | None = Field(default=None, description="送礼场景：长辈/孩子/情侣/朋友/聚会等")
    audience: str | None = Field(default=None, description="目标受众：女生/男生/女朋友/闺蜜等")
    max_price: float | None = Field(default=None, ge=0, description="预算上限（含），用户未明确时留空")
    in_stock_only: bool = Field(default=True, description="是否仅推荐有库存商品，默认 True")


class StockArguments(BaseModel):
    goods_name: str = Field(default="", max_length=100, description="蛋糕名称关键词")


class CurrentTimeArguments(BaseModel):
    pass


def business_tools() -> list[BaseTool]:
    @tool("get_order_status", args_schema=OrderQuery)
    async def get_order_status_tool(
        order_id: int | None = None,
        order_no: str | None = None,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """查询当前登录用户的订单；不传订单标识时返回最近订单。"""
        if runtime.context.user_id is None:
            return "当前登录身份无效，无法访问订单数据。"
        try:
            return await get_order_status(
                user_id=runtime.context.user_id,
                order_id=order_id,
                order_no=order_no,
            )
        except Exception:
            logger.exception("get_order_status tool failed")
            return "订单系统暂时不可用，请稍后重试。"

    @tool("cancel_order", args_schema=CancelOrderArguments)
    async def cancel_order_tool(
        order_id: int | None = None,
        order_no: str | None = None,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """将当前用户明确要求取消的订单标记为已取消，并原子恢复商品库存。

        必须提供且只提供 order_id 或 order_no。订单标识可以来自当前消息，也可以
        来自最近对话中已明确的唯一订单。用户直接说取消，或对包含同一订单标识的
        取消确认问题作肯定答复后调用；订单不明确时不要猜测，应先查询或询问。
        """
        context = runtime.context
        if context.user_id is None:
            return "当前登录身份无效，无法取消订单。"
        if not _has_confirmed_cancel(context, order_id, order_no):
            return "安全校验未通过：用户尚未明确确认取消该订单。"
        try:
            return await cancel_order(
                user_id=context.user_id,
                order_id=order_id,
                order_no=order_no,
            )
        except Exception:
            logger.exception("cancel_order tool failed")
            return "取消订单暂时失败，订单未被确认取消，请稍后重试。"

    @tool("recommend_cake", args_schema=RecommendationArguments)
    async def recommend_cake_tool(
        keywords: str = "",
        occasion: str | None = None,
        audience: str | None = None,
        max_price: float | None = None,
        in_stock_only: bool = True,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """根据用户的口味、用途或送礼场景推荐当前商城中的蛋糕；可叠加当前登录用户的个性化偏好。"""
        try:
            query = RecommendationQuery(
                keywords=keywords,
                occasion=occasion,
                audience=audience,
                max_price=max_price,
                in_stock_only=in_stock_only,
            )
            user_id = runtime.context.user_id if runtime and runtime.context else None
            return await recommend_cake(query, user_id=user_id)
        except Exception:
            logger.exception("recommend_cake tool failed")
            return "商品推荐服务暂时不可用，请稍后重试。"

    @tool("check_stock", args_schema=StockArguments)
    async def check_stock_tool(
        goods_name: str = "",
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """查询一个或多个蛋糕商品的实时库存。"""
        try:
            return await check_stock(goods_name=goods_name)
        except Exception:
            logger.exception("check_stock tool failed")
            return "库存服务暂时不可用，请稍后重试。"

    @tool("get_current_time", args_schema=CurrentTimeArguments)
    async def get_current_time_tool(
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """返回门店时区的当前日期、星期和时间，无需参数。

        用户询问现在、今天、星期、相对日期，或业务判断依赖当前时刻时调用。
        静态营业时间、固定配送时长等不依赖当前时刻的问题不需要调用。
        返回值采用配置的门店时区并包含 ISO 8601 偏移量，可直接用于时间计算。
        """
        now = datetime.now(_STORE_TIMEZONE)
        return (
            f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}\n"
            f"星期：{_WEEKDAYS[now.weekday()]}\n"
            f"时区：{APP_TIMEZONE}（UTC{now.strftime('%z')[:3]}:{now.strftime('%z')[3:]}）\n"
            f"ISO 8601：{now.isoformat(timespec='seconds')}"
        )

    return [
        get_order_status_tool,
        cancel_order_tool,
        recommend_cake_tool,
        check_stock_tool,
        get_current_time_tool,
    ]


__all__ = ["business_tools"]
