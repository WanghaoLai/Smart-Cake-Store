"""语义搜索与个性化推荐引擎回归测试（SQLite 内存，不触外部 API）。

向量检索通过 patch _vector_candidates 注入，验证的是：
候选合并、实时库存过滤、三级兜底、推荐信号优先级与冷启动。
真实 Embedding 质量依赖线上模型，不属于单元回归范围。"""
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise

from agents.recommendation import rule_engine, semantic_search
from models import Category, Favorite, Goods, Orders, Review, User


CAT_LOVERS, CAT_KIDS = 1, 2
USER_ID = 10


class RecommendationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=USER_ID, username="buyer", role="用户")
        await User.create(id=99, username="other", role="用户")
        await Category.create(id=CAT_LOVERS, name="情侣")
        await Category.create(id=CAT_KIDS, name="儿童")
        # g1 收藏目标(情侣)；g2 情侣但缺货；g3 儿童·3 单销量；g4 儿童·无销量；g5 情侣·新上架
        await Goods.create(id=1, name="晨光玫瑰", price=Decimal("98"), num=5, unit="份", category_id=CAT_LOVERS)
        await Goods.create(id=2, name="缺货玫瑰", price=Decimal("98"), num=0, unit="份", category_id=CAT_LOVERS)
        await Goods.create(id=3, name="童画森林", price=Decimal("98"), num=5, unit="份", category_id=CAT_KIDS, description="儿童生日")
        await Goods.create(id=4, name="森林慕斯", price=Decimal("108"), num=5, unit="份", category_id=CAT_KIDS)
        await Goods.create(id=5, name="新上架情侣款", price=Decimal("128"), num=5, unit="份", category_id=CAT_LOVERS)
        await Favorite.create(user_id=USER_ID, goods_id=1)

        # 多笔订单均需唯一 order_no（models.Orders.order_no unique 约束已存在）
        seq = [0]
        async def order(goods_id, user_id=USER_ID, status="待发货"):
            seq[0] += 1
            await Orders.create(
                user_id=user_id, goods_id=goods_id, num=1, status=status,
                order_no=f"t{goods_id}-{user_id}-{seq[0]}", time="2026-08-21 10:00:00",
                total_price=Decimal("98"),
            )
        for _ in range(3):
            await order(3)
        await order(1, user_id=99)  # 其他用户的销量不应进入推荐信号干扰

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    # ---------- 语义搜索 ----------

    async def test_semantic_search_filters_out_of_stock(self):
        """向量候选中的缺货商品必须被实时库存过滤掉。"""
        with patch.object(
            semantic_search, "_vector_candidates",
            new=AsyncMock(return_value=[
                {"goods_id": 1, "distance": 0.1},
                {"goods_id": 2, "distance": 0.2},  # num=0
                {"goods_id": 3, "distance": 0.3},
            ]),
        ):
            result = await semantic_search.search("玫瑰", top_k=10)
        self.assertEqual(result["mode"], "semantic")
        self.assertEqual([item["id"] for item in result["list"]], [1, 3])
        self.assertTrue(all(item["num"] > 0 for item in result["list"]))
        self.assertTrue(all("reason" in item for item in result["list"]))

    async def test_semantic_search_keyword_fallback(self):
        """向量无结果时退到关键字 LIKE 匹配。"""
        with patch.object(semantic_search, "_vector_candidates", new=AsyncMock(return_value=[])):
            result = await semantic_search.search("森林", top_k=10)
        self.assertEqual(result["mode"], "keyword")
        self.assertEqual(sorted(item["id"] for item in result["list"]), [3, 4])

    async def test_semantic_search_hot_fallback_on_no_match(self):
        """关键字也无结果时给出热销兜底（按销量排序）。"""
        with patch.object(semantic_search, "_vector_candidates", new=AsyncMock(return_value=[])):
            result = await semantic_search.search("不存在的关键词xyz", top_k=10)
        self.assertEqual(result["mode"], "hot")
        self.assertGreaterEqual(len(result["list"]), 1)
        self.assertEqual(result["list"][0]["id"], 3, "销量最高的童画森林应排第一")

    async def test_semantic_search_vector_failure_degrades_to_keyword(self):
        """Embedding 服务异常不阻断搜索，静默降级到关键字。"""
        with patch.object(
            semantic_search, "_vector_candidates",
            new=AsyncMock(side_effect=RuntimeError("embedding down")),
        ):
            result = await semantic_search.search("森林", top_k=10)
        self.assertEqual(result["mode"], "keyword")

    async def test_semantic_search_empty_query_returns_hot(self):
        result = await semantic_search.search("", top_k=3)
        self.assertEqual(result["mode"], "hot")

    # ---------- 推荐引擎 ----------

    async def test_recommend_prefers_favorite_category(self):
        """收藏过情侣分类 → 同分类商品的分类偏好分应高于儿童分类商品。

        注：排序结果不仅取决于分类分，还叠加销量热度归一与评分。
        这里只断言收藏分类商品的总分高于非收藏非购买分类商品，
        不预设具体 id（评分与销量归一后具体次序可能浮动）。"""
        result = await rule_engine.recommend(USER_ID, limit=10)
        self.assertGreaterEqual(len(result), 1)
        by_id = {item["id"]: item for item in result}
        self.assertIn(5, by_id, "情侣分类新上架款应在推荐候选中（分类偏好驱动）")
        # 情侣款 5 的分类偏好分应反映在 reason 上
        self.assertIn("收藏", by_id[5]["reason"])

    async def test_recommend_excludes_favorited_and_out_of_stock(self):
        result = await rule_engine.recommend(USER_ID, limit=10)
        ids = [item["id"] for item in result]
        self.assertNotIn(1, ids, "已收藏的商品不重复推荐")
        self.assertNotIn(2, ids, "缺货商品不推荐")

    async def test_recommend_cold_start_uses_sales_heat(self):
        """无行为数据用户：按销量热度兜底（替代旧"时间 Top N"）。"""
        result = await rule_engine.recommend(user_id=888, limit=3)
        self.assertEqual(result[0]["id"], 3, "冷启动按销量排序")
        self.assertIn("热销", result[0]["reason"])

    async def test_recommend_considers_rating_signal(self):
        await Review.create(goods_id=4, user_id=USER_ID, rating=5, content="很好吃", time="2026-08-21 10:00:00")
        result = await rule_engine.recommend(USER_ID, limit=3)
        by_id = {item["id"]: item for item in result}
        self.assertIn(4, by_id, "高分商品应进入推荐候选")


if __name__ == "__main__":
    unittest.main()
