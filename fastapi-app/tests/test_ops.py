"""商品分析测试（SQLite 内存，不触 LLM）。

覆盖不变量：
  - 情感分类（星级主判据 + 词典修正 + 否定前缀）
  - 库存健康分与综合评分纯函数
  - 四维分析 SQL 路径与 Markdown 报告渲染
  - 运营 Agent 装配一致性（工具白名单顺序）"""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from tortoise import Tortoise

from agents.ops.analysis import (
    build_product_fact_snapshot,
    classify_sentiment,
    composite_score,
    inventory_analysis,
    inventory_score,
    product_performance,
    review_analysis,
    sales_analysis,
    stock_level,
)
from agents.ops.report import build_fact_digest, build_product_markdown
from models import Goods, Orders, Review, User


class SentimentPureTests(unittest.TestCase):
    """情感分类：星级主判据、负向词覆盖、3 星词典修正、否定前缀。"""

    def test_rating_dominant(self):
        self.assertEqual(classify_sentiment(5, "很好吃"), "好评")
        self.assertEqual(classify_sentiment(2, "不错"), "差评")
        self.assertEqual(classify_sentiment(1, ""), "差评")

    def test_negative_term_overrides_high_rating(self):
        self.assertEqual(classify_sentiment(5, "样子好看但是太甜了"), "差评")

    def test_three_star_uses_lexicon(self):
        self.assertEqual(classify_sentiment(3, "味道挺好，好吃"), "好评")
        self.assertEqual(classify_sentiment(3, "有点失望，量少"), "差评")
        self.assertEqual(classify_sentiment(3, "一般的蛋糕"), "中评")

    def test_negation_prefix_blocks_positive(self):
        # "不好吃"不命中"好吃"，3 星且无其他信号 → 中评
        self.assertEqual(classify_sentiment(3, "不好吃"), "中评")


class ScorePureTests(unittest.TestCase):
    """库存健康分与综合评分的确定性数学。"""

    def test_inventory_score_ideal_window(self):
        self.assertEqual(inventory_score(10, 30, 30), 100)   # 可售 10 天 ∈ [7,30]

    def test_inventory_score_low_stock(self):
        self.assertEqual(inventory_score(2, 30, 30), 64)     # 50 + 50*2/7

    def test_inventory_score_overstock(self):
        self.assertEqual(inventory_score(20, 10, 30), 80)    # 可售 60 天衰减

    def test_inventory_score_edge_cases(self):
        self.assertEqual(inventory_score(0, 5, 30), 20)      # 售罄且有销量
        self.assertEqual(inventory_score(50, 0, 30), 40)     # 有货零销量

    def test_composite_no_reviews_neutral(self):
        result = composite_score(0, 0, 10, 10, 20, 10, 30)
        self.assertEqual(result["dimensions"]["review"]["score"], 60)
        self.assertTrue(any("暂无评价" in s for s in result["suggestions"]))

    def test_composite_grade_a(self):
        result = composite_score(avg_rating=4.8, review_count=10, goods_qty=30,
                                 top_qty=30, stock=20, sold_qty=30, days=30)
        self.assertEqual(result["dimensions"]["sales"]["score"], 100)
        self.assertEqual(result["grade"], "A")

    def test_stock_levels(self):
        self.assertEqual(stock_level(0), "售罄")
        self.assertEqual(stock_level(3), "紧张")
        self.assertEqual(stock_level(10), "偏低")
        self.assertEqual(stock_level(99), "健康")


class ProductAnalysisSqlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=1, username="buyer", role="用户")
        await Goods.create(id=1, name="草莓蛋糕", price=Decimal("98"), num=4, unit="份")
        await Goods.create(id=2, name="巧克力蛋糕", price=Decimal("108"), num=30, unit="份")
        await Goods.create(id=3, name="下架款", price=Decimal("58"), num=0, unit="份")
        now = datetime.now(timezone.utc)
        t_today = now.strftime("%Y-%m-%d %H:%M:%S")
        t_yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        # 商品1：好评 1 + 差评 2（2 星直接差评；3 星带负词判差评）
        await Review.create(goods_id=1, user_id=1, rating=5, content="很好吃，口感细腻", time=t_today)
        await Review.create(goods_id=1, user_id=1, rating=2, content="太甜了，量少", time=t_yesterday)
        await Review.create(goods_id=1, user_id=1, rating=3, content="有点失望，太甜", time=t_yesterday)
        await Orders.create(user_id=1, goods_id=1, num=1, status="待发货",
                            order_no="a1", time=t_today, total_price=Decimal("98"))
        await Orders.create(user_id=1, goods_id=1, num=2, status="已发货",
                            order_no="a2", time=t_yesterday, total_price=Decimal("196"))
        await Orders.create(user_id=1, goods_id=1, num=1, status="已取消",
                            order_no="a3", time=t_today, total_price=Decimal("98"))

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_review_analysis_sentiment_and_focus(self):
        data = await review_analysis(1, days=30)
        self.assertEqual(data["sentiment"], {"好评": 1, "中评": 0, "差评": 2})
        terms = [f["term"] for f in data["negative_focus"]]
        self.assertIn("太甜", terms)
        self.assertEqual(len(data["negative_reviews"]), 2)
        # 真实好评摘录：供 AI 分析引用真实用户声音
        self.assertEqual(len(data["positive_reviews"]), 1)
        self.assertIn("好吃", data["positive_reviews"][0]["content"])

    async def test_sales_analysis_excludes_cancelled(self):
        data = await sales_analysis(1, days=30)
        self.assertEqual(data["total_qty"], 3)        # 1 + 2，取消单不计
        self.assertEqual(data["order_count"], 2)
        self.assertEqual(len(data["daily_trend"]), 30)

    async def test_inventory_analysis_levels_and_warning(self):
        data = await inventory_analysis(days=30)
        self.assertEqual(data["levels"]["紧张"], 1)    # 商品1 num=4
        self.assertEqual(data["levels"]["售罄"], 1)    # 商品3
        names = [w["name"] for w in data["warning_list"]]
        self.assertIn("草莓蛋糕", names)               # 紧张且有销量 → 预警

    async def test_product_performance_pipeline(self):
        data = await product_performance(1, days=30)
        self.assertIn(data["score"]["grade"], "ABCD")
        self.assertIn("sales", data["score"]["dimensions"])
        self.assertEqual(data["stock"], 4)

    async def test_fact_snapshot_reuses_sql_aggregates(self):
        facts = await build_product_fact_snapshot(1, days=30)
        self.assertEqual(facts["sales"]["total_qty"], 3)
        self.assertEqual(facts["performance"]["stock"], 4)
        warning_names = [row["name"] for row in facts["inventory"]["warning_list"]]
        self.assertIn("草莓蛋糕", warning_names)

    async def test_build_product_markdown(self):
        perf = await product_performance(1, days=30)
        reviews = await review_analysis(1, days=30)
        md = build_product_markdown(
            {"kind": "product_analysis", "goods_name": "草莓蛋糕", "days": 30,
             "performance": perf, "reviews": reviews, "sales": {"total_qty": 3},
             "inventory": {"levels": {}, "warning_list": [], "total_inventory_value": 0}},
            summary=None,
        )
        self.assertIn("# 商品分析报告 · 草莓蛋糕", md)
        self.assertIn("模型暂不可用", md)              # 降级说明
        self.assertIn("太甜", md)

    async def test_build_fact_digest_grounded_numbers(self):
        """AI 注入摘要必须携带真实销量与真实评价原文，失真即测试失败。"""
        perf = await product_performance(1, days=30)
        reviews = await review_analysis(1, days=30)
        sales = await sales_analysis(1, days=30)
        digest = build_fact_digest({
            "goods_id": 1, "goods_name": "草莓蛋糕", "days": 30,
            "performance": perf, "reviews": reviews, "sales": sales,
        })
        self.assertIn("服务端已核实的真实数据", digest)
        self.assertIn(f"窗口销量 {sales['total_qty']} 件", digest)
        self.assertIn(f"共 {reviews['total']} 条", digest)
        self.assertIn("真实差评摘录", digest)
        self.assertIn("太甜", digest)                    # 差评聚焦进入摘要
        self.assertIn("禁止出现上述数据与工具结果之外的任何数字", digest)


class OpsAgentAssemblyTests(unittest.TestCase):
    """装配一致性：profile 白名单顺序 == 实际工具顺序；NoGrounding 空取证。"""

    def test_ops_agent_tools_match_profile(self):
        from agents.factory import create_ops_agent
        agent = create_ops_agent()
        self.assertEqual(agent.profile.name, "smart_mall_product_analyst")
        self.assertEqual([t.name for t in agent.tools], agent.profile.tools)

    def test_no_grounding_returns_empty(self):
        from agents.ops import NoGrounding
        import asyncio
        self.assertEqual(asyncio.run(NoGrounding().collect("分析商品", 1)), [])


if __name__ == "__main__":
    unittest.main()
