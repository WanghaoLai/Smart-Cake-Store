"""商品分析与运营洞察 API。

两类能力：
  1. 确定性分析（/ops/analysis/*）：SQL + 规则直出事实，前端卡片渲染；
  2. AI 分析（POST /ops/analysis/ai）：运营 Agent 按需调用分析工具产出结论，
     与确定性事实并列返回并落库 OpsReport，支持 Markdown 报告下载。
全部管理员鉴权。"""
import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from agents.agent import AgentUnavailableError
from agents.factory import create_ops_agent
from agents.ops.analysis import (
    inventory_analysis,
    product_performance,
    review_analysis,
    sales_analysis,
)
from agents.ops.report import build_fact_digest, build_product_markdown
from common.auth import get_current_admin
from common.exception_handler import CustomException
from common.result import Result
from models import Goods, OpsReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", dependencies=[Depends(get_current_admin)])

ops_agent = create_ops_agent()


class ProductAnalysisRequest(BaseModel):
    goods_id: int = Field(gt=0)
    days: int = Field(default=30, ge=1, le=90)


def _clamp_days(days: int, lo: int = 1, hi: int = 90) -> int:
    return min(max(days, lo), hi)


async def _get_goods(goods_id: int) -> Goods:
    goods = await Goods.get_or_none(id=goods_id)
    if goods is None:
        raise CustomException("商品不存在")
    return goods


@router.get("/products")
async def list_products():
    """商品选择器：轻量列表（含库存与分类），供分析页下拉框使用。"""
    goods_list = await Goods.all().prefetch_related("category").order_by("-id")
    items = [
        {
            "id": g.id,
            "name": g.name,
            "category": g.category.name if g.category else "未分类",
            "price": float(g.price) if g.price is not None else 0,
            "stock": g.num or 0,
        }
        for g in goods_list
    ]
    return Result.success(items)


@router.get("/analysis/reviews")
async def get_review_analysis(goods_id: int, days: int = 30):
    """评价分析：情感分布、关键词、差评聚焦。"""
    await _get_goods(goods_id)
    return Result.success(await review_analysis(goods_id, _clamp_days(days)))


@router.get("/analysis/sales")
async def get_sales_analysis(goods_id: int | None = None, days: int = 30):
    """销量分析：带 goods_id 为单商品趋势与环比；不带为全店热销/滞销排行。"""
    if goods_id is not None:
        await _get_goods(goods_id)
    return Result.success(await sales_analysis(goods_id, _clamp_days(days)))


@router.get("/analysis/inventory")
async def get_inventory_analysis(days: int = 30):
    """库存分析：水位分布、资金占用、预警清单。"""
    return Result.success(await inventory_analysis(_clamp_days(days)))


@router.get("/analysis/performance")
async def get_performance_analysis(goods_id: int, days: int = 30):
    """综合表现：销量 × 评价 × 库存联动评分与建议。"""
    await _get_goods(goods_id)
    return Result.success(await product_performance(goods_id, _clamp_days(days)))


@router.post("/analysis/ai")
async def ai_product_analysis(payload: ProductAnalysisRequest):
    """AI 分析入口：Agent 调用分析工具生成结论，与确定性事实并列返回。

    LLM 不可用时降级为 facts-only（degraded=True），管理员仍可下载报告。"""
    goods = await _get_goods(payload.goods_id)
    days = _clamp_days(payload.days)

    # 确定性事实：无论 LLM 是否可用都返回，支撑页面卡片与报告下载
    performance, reviews, sales, inventory = await asyncio.gather(
        product_performance(goods.id, days),
        review_analysis(goods.id, days),
        sales_analysis(goods.id, days),
        inventory_analysis(days),
    )
    facts = {
        "kind": "product_analysis",
        "goods_id": goods.id,
        "goods_name": goods.name,
        "days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "performance": performance,
        "reviews": reviews,
        "sales": sales,
        "inventory": inventory,
    }

    answer = None
    degraded = False
    if ops_agent.configured:
        # 注入服务端已核实的真实订单销量与用户评价摘要（Grounding 哲学：
        # 关键事实不依赖模型主动调工具），工具仅用于补充全店视角。
        message = (
            f"{build_fact_digest(facts)}\n\n"
            f"请对商品「{goods.name}」生成近 {days} 天的分析结论与可执行建议。"
        )
        try:
            answer = await ops_agent.process_message(message, history=[])
        except AgentUnavailableError:
            logger.exception(
                "ops agent failed: goods_id=%s days=%s", goods.id, days,
            )
            degraded = True
    else:
        degraded = True

    report = await OpsReport.create(
        days=days,
        summary=answer,
        facts=facts,
        model=None if degraded else ops_agent.profile.name,
    )
    return Result.success({
        "report_id": report.id,
        "goods_id": goods.id,
        "goods_name": goods.name,
        "days": days,
        "answer": answer,
        "degraded": degraded,
        "facts": facts,
    })


@router.get("/analysis/report/{report_id}")
async def download_product_report(report_id: int):
    """下载 Markdown 分析报告（按落库的 facts 渲染，不重复调用 LLM）。"""
    report = await OpsReport.get_or_none(id=report_id)
    if report is None:
        raise CustomException("报告不存在")
    facts = report.facts if isinstance(report.facts, dict) else {}
    if facts.get("kind") != "product_analysis":
        raise CustomException("该报告不是商品分析报告")
    markdown = build_product_markdown(facts, report.summary)
    filename = quote(f"商品分析报告_{facts.get('goods_name', '')}_{report.id}.md")
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
