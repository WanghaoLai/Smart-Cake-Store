import unittest
from unittest.mock import AsyncMock, patch

from agents.agent.grounding import GroundingService


class FakeKnowledgeService:
    def __init__(self):
        self.queries = []

    def search_documents(self, query, top_k):
        self.queries.append((query, top_k))
        return [{"content": "门店营业时间为 9:00-21:00"}]


class GroundingServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_product_question_collects_vector_and_mysql_evidence(self):
        knowledge = FakeKnowledgeService()
        service = GroundingService(knowledge, top_k=2)
        with patch(
            "agents.agent.grounding.get_product_facts",
            new=AsyncMock(return_value="草莓蛋糕｜价格 ¥88｜库存 3个"),
        ) as product_facts:
            evidence = await service.collect("草莓蛋糕还有货吗", user_id=7)

        self.assertEqual([item.source for item in evidence], ["ChromaDB知识库", "MySQL实时商品"])
        self.assertEqual(knowledge.queries, [("草莓蛋糕还有货吗", 2)])
        product_facts.assert_awaited_once_with("草莓蛋糕还有货吗")

    async def test_order_question_is_scoped_to_authenticated_user(self):
        service = GroundingService(FakeKnowledgeService())
        with patch(
            "agents.agent.grounding.get_order_status",
            new=AsyncMock(return_value="订单 1001：待发货"),
        ) as order_status:
            evidence = await service.collect("我的订单状态", user_id=23)

        order_status.assert_awaited_once_with(user_id=23)
        self.assertIn("MySQL当前用户订单", [item.source for item in evidence])

    async def test_greeting_does_not_query_business_sources(self):
        knowledge = FakeKnowledgeService()
        evidence = await GroundingService(knowledge).collect("你好", user_id=7)
        self.assertEqual(evidence, [])
        self.assertEqual(knowledge.queries, [])

    async def test_product_followup_uses_recent_conversation_intent(self):
        knowledge = FakeKnowledgeService()
        service = GroundingService(knowledge)
        history = [
            {"role": "user", "content": "推荐一款生日蛋糕"},
            {"role": "assistant", "content": "请问送给谁？"},
        ]
        with patch(
            "agents.agent.grounding.get_product_facts",
            new=AsyncMock(return_value="福寿安康祝寿蛋糕｜价格 ¥108"),
        ) as product_facts:
            evidence = await service.collect("送长辈", user_id=7, history=history)

        self.assertIn("MySQL实时商品", [item.source for item in evidence])
        called_query = product_facts.await_args.args[0]
        self.assertIn("推荐一款生日蛋糕", called_query)
        self.assertIn("送长辈", called_query)


if __name__ == "__main__":
    unittest.main()
