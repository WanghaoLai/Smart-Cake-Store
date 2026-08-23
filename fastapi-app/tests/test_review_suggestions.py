"""代码审查建议项的专项回归测试。"""
import asyncio
import unittest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError

from api.goods import GoodsCreate, GoodsUpdate
from api.chat import MessageRequest, get_messages, send_message, send_rate_limiter
from agents.agent.executor import AgentInvocation
from agents.rag.index_tasks import IndexTaskService
from agents.tools.product.detail import build_verified_product_answer, extract_product_ids
from common.auth import get_current_customer
from common.exception_handler import ConflictException, setup_exceptions
from common.time import format_store_time
from models import Conversation, Goods, IndexTask, Message, User


class RoleBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_customer_dependency_rejects_admin_even_when_ids_overlap(self):
        with self.assertRaises(HTTPException) as ctx:
            await get_current_customer({"user_id": 1, "username": "admin", "role": "管理员"})
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_utc_values_are_converted_only_at_presentation_boundary(self):
        value = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(format_store_time(value), "2026-08-23 08:00:00")


class HttpStatusSemanticsTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        setup_exceptions(app)

        @app.get("/conflict")
        async def conflict():
            raise ConflictException("状态冲突")

        @app.get("/validation")
        async def validation(value: int):
            return value

        @app.get("/crash")
        async def crash():
            raise RuntimeError("private detail")

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_business_validation_and_unknown_errors_use_real_http_statuses(self):
        self.assertEqual(self.client.get("/conflict").status_code, 409)
        self.assertEqual(self.client.get("/validation", params={"value": "x"}).status_code, 422)
        response = self.client.get("/crash")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private detail", response.text)


class GoodsWriteContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    def test_create_requires_valid_core_fields(self):
        valid = GoodsCreate(name="  草莓蛋糕  ", price="88.50", num=3)
        self.assertEqual(valid.name, "草莓蛋糕")
        self.assertEqual(valid.price, Decimal("88.50"))
        for payload in (
            {"price": 10, "num": 1},
            {"name": "蛋糕", "price": -1, "num": 1},
            {"name": "蛋糕", "price": 1, "num": -1},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                GoodsCreate(**payload)

    def test_update_requires_id_and_at_least_one_change(self):
        with self.assertRaises(ValidationError):
            GoodsUpdate(id=1)
        self.assertEqual(GoodsUpdate(id=1, num=0).num, 0)

    async def test_database_rejects_null_core_fields(self):
        with self.assertRaises((ValueError, IntegrityError)):
            await Goods.create(name="坏数据", price=None, num=1)


class ProductFactRenderingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await Goods.create(id=7, name="数据库蛋糕", price=Decimal("66.00"), num=2, unit="份")

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    def test_only_structured_ids_are_accepted_from_model(self):
        self.assertEqual(extract_product_ids('说明 {"product_ids":[7,"8",7]}'), [7, 8])
        self.assertEqual(extract_product_ids("数据库蛋糕 ¥1 库存999"), [])

    async def test_names_prices_and_stock_are_rendered_from_database(self):
        answer = await build_verified_product_answer("忽略", product_ids=[7, 999])
        self.assertIn("数据库蛋糕", answer)
        self.assertIn("¥66.00", answer)
        self.assertIn("库存 2份", answer)


class ChatBoundedHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=3, username="chat-user", role="用户")
        self.current_user = {"user_id": 3, "username": "chat-user", "role": "用户"}
        self.conversation = await Conversation.create(user_id=3, owner_role="用户")
        for index in range(30):
            await Message.create(
                conversation_id=self.conversation.id,
                role="user" if index % 2 == 0 else "assistant",
                content=f"history-{index}",
            )

    async def asyncTearDown(self):
        send_rate_limiter.reset("用户:3")
        await Tortoise.close_connections()

    async def test_message_list_is_paginated_from_latest_and_keeps_order(self):
        result = await get_messages(self.conversation.id, 1, 5, self.current_user)
        self.assertEqual(result.data["total"], 30)
        self.assertEqual([row["content"] for row in result.data["list"]], [
            "history-25", "history-26", "history-27", "history-28", "history-29",
        ])

    async def test_send_loads_only_agent_history_limit_in_sql(self):
        invocation = AgentInvocation(answer="ok")
        with patch("api.chat.customer_service_agent.invoke", new=AsyncMock(return_value=invocation)) as invoke:
            response = await send_message(
                MessageRequest(conversation_id=self.conversation.id, message="latest"),
                self.current_user,
            )
            async for _ in response.body_iterator:
                pass
        supplied_history = invoke.await_args.args[1]
        self.assertLessEqual(len(supplied_history), 20)
        self.assertEqual(supplied_history[-1]["content"], "history-29")
        self.assertNotIn("history-0", [row["content"] for row in supplied_history])


class IndexTaskClaimTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await Goods.create(id=9, name="索引蛋糕", price=10, num=1)
        self.task = await IndexTask.create(entity_type="goods", entity_id=9, action="upsert")

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_concurrent_workers_claim_task_exactly_once(self):
        store = unittest.mock.MagicMock()
        service = IndexTaskService(store)
        results = await asyncio.gather(service.process(self.task.id), service.process(self.task.id))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(store.sync_goods.call_count, 1)
        task = await IndexTask.get(id=self.task.id)
        self.assertEqual((task.status, task.attempts, task.claim_token), ("done", 1, None))


if __name__ == "__main__":
    unittest.main()
