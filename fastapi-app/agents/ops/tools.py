"""运营分析 LangChain 工具：供运营 Agent 按需调用获取结构化事实。

与 business.py 同一纪律：@tool 只做参数 schema、异常隔离与结果格式化，
分析逻辑全部在 analysis.py（可单测、可被 API 直接复用）。"""
import logging

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from agents.agent import AgentContext
from agents.ops.analysis import (
    inventory_analysis,
    product_performance,
    review_analysis,
    sales_analysis,
)

logger = logging.getLogger(__name__)


class ReviewAnalysisArgs(BaseModel):
    goods_id: int = Field(gt=0, description="商品数据库 ID")
    days: int = Field(default=30, ge=1, le=90, description="统计时间窗（天）")


class SalesAnalysisArgs(BaseModel):
    goods_id: int | None = Field(default=None, gt=0, description="商品 ID；不传则返回全店热销/滞销排行")
    days: int = Field(default=30, ge=1, le=90, description="统计时间窗（天）")


class InventoryArgs(BaseModel):
    days: int = Field(default=30, ge=1, le=90, description="用于估算可售天数的销量窗口（天）")


class PerformanceArgs(BaseModel):
    goods_id: int = Field(gt=0, description="商品数据库 ID")
    days: int = Field(default=30, ge=1, le=90, description="统计时间窗（天）")


def _fmt(data: dict) -> str:
    import json
    return json.dumps(data, ensure_ascii=False)


class NoGrounding:
    """运营 Agent 的取证策略：不做客服式前置注入。

    分析事实由专用工具按需提供（更结构化），前置注入只会增加延迟；
    同时避免执行器对含"库存/¥"字样的分析长回答触发客服侧商品答案校验。"""

    async def collect(self, message, user_id, history=None):
        return []


def analysis_tools() -> list[BaseTool]:
    @tool("analyze_product_reviews", args_schema=ReviewAnalysisArgs)
    async def analyze_product_reviews_tool(
        goods_id: int,
        days: int = 30,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """分析指定商品的评价：平均星级、好评/中评/差评分布、好评率、
        高频关键词、差评聚焦（负向问题类型）与差评原文。"""
        try:
            return _fmt(await review_analysis(goods_id, days))
        except Exception:
            logger.exception("analyze_product_reviews tool failed")
            return "评价分析暂时不可用，请稍后重试。"

    @tool("analyze_product_sales", args_schema=SalesAnalysisArgs)
    async def analyze_product_sales_tool(
        goods_id: int | None = None,
        days: int = 30,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """分析销量：指定商品返回按天销量趋势、总量、营收与环比；
        不指定商品返回全店热销与滞销排行（含库存与价格）。"""
        try:
            return _fmt(await sales_analysis(goods_id, days))
        except Exception:
            logger.exception("analyze_product_sales tool failed")
            return "销量分析暂时不可用，请稍后重试。"

    @tool("analyze_inventory_status", args_schema=InventoryArgs)
    async def analyze_inventory_status_tool(
        days: int = 30,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """分析全店库存：库存水位分布（健康/偏低/紧张/售罄）、库存资金占用、
        预警商品清单（补货紧急或可售天数不足）。"""
        try:
            return _fmt(await inventory_analysis(days))
        except Exception:
            logger.exception("analyze_inventory_status tool failed")
            return "库存分析暂时不可用，请稍后重试。"

    @tool("analyze_product_performance", args_schema=PerformanceArgs)
    async def analyze_product_performance_tool(
        goods_id: int,
        days: int = 30,
        runtime: ToolRuntime[AgentContext] = None,
    ) -> str:
        """计算指定商品的综合表现评分：销量分、评价分、库存健康分加权合成，
        输出 A/B/C/D 等级、维度明细与确定性运营建议。"""
        try:
            return _fmt(await product_performance(goods_id, days))
        except Exception:
            logger.exception("analyze_product_performance tool failed")
            return "综合表现分析暂时不可用，请稍后重试。"

    return [
        analyze_product_reviews_tool,
        analyze_product_sales_tool,
        analyze_inventory_status_tool,
        analyze_product_performance_tool,
    ]


__all__ = ["NoGrounding", "analysis_tools"]
