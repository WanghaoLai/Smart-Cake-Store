"""LangChain tools for authenticated cake-store business operations."""

import logging

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, model_validator

from agents.context import AgentContext
from agents.tools import business_repository


logger = logging.getLogger(__name__)


class OrderQuery(BaseModel):
    order_id: int | None = Field(default=None, gt=0, description="订单数据库 ID")
    order_no: str | None = Field(default=None, max_length=64, description="业务订单号")


class CancelOrderArguments(OrderQuery):
    @model_validator(mode="after")
    def require_order_identifier(self):
        if self.order_id is None and not self.order_no:
            raise ValueError("必须提供 order_id 或 order_no")
        return self


class RecommendationArguments(BaseModel):
    preference: str = Field(default="", max_length=100, description="口味、场景或送礼对象")


class StockArguments(BaseModel):
    goods_name: str = Field(default="", max_length=100, description="蛋糕名称关键词")


def business_tools() -> list[BaseTool]:
    @tool("get_order_status", args_schema=OrderQuery)
    async def get_order_status_tool(
        order_id: int | None = None,
        order_no: str | None = None,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """查询当前登录用户的订单；不传订单标识时返回最近订单。"""
        context = runtime.context
        if context.user_id is None:
            return "当前登录身份无效，无法访问订单数据。"
        try:
            return await business_repository.get_order_status(
                user_id=context.user_id,
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
        """取消当前登录用户的订单并恢复库存；仅在用户当前消息明确要求取消时使用。"""
        context = runtime.context
        if context.user_id is None:
            return "当前登录身份无效，无法取消订单。"
        intent = context.user_message.lower()
        if not any(word in intent for word in ("取消", "撤销", "退订", "不要了", "cancel")):
            return "安全校验未通过：用户没有在当前消息中明确要求取消订单。"
        try:
            return await business_repository.cancel_order(
                user_id=context.user_id,
                order_id=order_id,
                order_no=order_no,
            )
        except Exception:
            logger.exception("cancel_order tool failed")
            return "取消订单暂时失败，订单未被确认取消，请稍后重试。"

    @tool("recommend_cake", args_schema=RecommendationArguments)
    async def recommend_cake_tool(
        preference: str = "",
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """根据用户的口味、用途或送礼场景推荐当前商城中的蛋糕。"""
        try:
            return await business_repository.recommend_cake(preference=preference)
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
            return await business_repository.check_stock(goods_name=goods_name)
        except Exception:
            logger.exception("check_stock tool failed")
            return "库存服务暂时不可用，请稍后重试。"

    return [get_order_status_tool, cancel_order_tool, recommend_cake_tool, check_stock_tool]
