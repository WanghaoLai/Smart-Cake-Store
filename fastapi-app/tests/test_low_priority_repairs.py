"""低优先级修复的业务不变量测试。"""
import unittest
import uuid
from decimal import Decimal

from tortoise import Tortoise

from agents.tools.order.repository import cancel_order
from agents.ops.analysis import _inventory_from_snapshot
from agents.ops.report import build_product_markdown
from api.orders import OrdersCreatePydantic, add as order_add, update_status
from common.exception_handler import ConflictException
from domain.order_status import ORDER_CANCELLED, ORDER_PENDING, ORDER_SHIPPED
from models import Address, AuditLog, Goods, Notification, Orders, User, WalletTransaction


ADMIN = {"user_id": 1, "username": "admin", "role": "管理员"}
USER = {"user_id": 2, "username": "buyer", "role": "用户"}


class ShippedOrderCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=USER["user_id"], username="buyer", role="用户", balance=Decimal("100"))
        await Address.create(id=1, user_id=USER["user_id"], name="买家", phone="13800000000", address="测试地址")
        await Goods.create(id=1, name="配送中蛋糕", price=Decimal("60"), num=5, unit="份")

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def _place_and_ship(self) -> Orders:
        await order_add(
            OrdersCreatePydantic(
                request_id=uuid.uuid4().hex,
                goodsId=1,
                addressId=1,
                num=1,
            ),
            USER,
        )
        order = await Orders.all().first()
        await update_status(order.id, ORDER_SHIPPED, ADMIN)
        return order

    async def test_api_rejects_shipped_order_without_refund_or_stock_restore(self):
        order = await self._place_and_ship()
        notifications_before = await Notification.all().count()
        audits_before = await AuditLog.all().count()

        with self.assertRaises(ConflictException):
            await update_status(order.id, ORDER_CANCELLED, USER)

        self.assertEqual((await Orders.get(id=order.id)).status, ORDER_SHIPPED)
        self.assertEqual((await Goods.get(id=1)).num, 4)
        self.assertEqual((await User.get(id=USER["user_id"])).balance, Decimal("40"))
        self.assertEqual(await WalletTransaction.filter(type="refund").count(), 0)
        self.assertEqual(await Notification.all().count(), notifications_before)
        self.assertEqual(await AuditLog.all().count(), audits_before)

    async def test_agent_uses_same_shipped_order_boundary(self):
        order = await self._place_and_ship()
        result = await cancel_order(USER["user_id"], order_id=order.id)

        self.assertIn("不允许取消", result)
        self.assertEqual((await Orders.get(id=order.id)).status, ORDER_SHIPPED)
        self.assertEqual((await Goods.get(id=1)).num, 4)
        self.assertEqual(await WalletTransaction.filter(type="refund").count(), 0)

    async def test_pending_order_remains_cancellable(self):
        await order_add(
            OrdersCreatePydantic(
                request_id=uuid.uuid4().hex,
                goodsId=1,
                addressId=1,
                num=1,
            ),
            USER,
        )
        order = await Orders.all().first()
        self.assertEqual(order.status, ORDER_PENDING)

        await update_status(order.id, ORDER_CANCELLED, USER)

        self.assertEqual((await Orders.get(id=order.id)).status, ORDER_CANCELLED)
        self.assertEqual((await Goods.get(id=1)).num, 5)
        self.assertEqual((await User.get(id=USER["user_id"])).balance, Decimal("100"))

class InventoryValuationWordingTests(unittest.TestCase):
    def test_inventory_value_declares_retail_price_basis(self):
        goods = Goods(id=1, name="零售价蛋糕", price=Decimal("80"), num=3, unit="份")
        result = _inventory_from_snapshot({
            "days": 30,
            "goods": {1: goods},
            "sales": {},
        })
        self.assertEqual(result["valuation_basis"], "retail_price")
        self.assertEqual(result["total_inventory_value"], 240.0)

    def test_downloaded_report_does_not_call_retail_value_funding(self):
        report = build_product_markdown({
            "goods_name": "测试蛋糕",
            "days": 30,
            "performance": {"score": {"dimensions": {}, "suggestions": []}},
            "reviews": {"sentiment": {}},
            "sales": {"daily_trend": []},
            "inventory": {
                "levels": {},
                "total_inventory_value": 240,
                "warning_count": 0,
                "warning_list": [],
            },
        }, None)
        self.assertIn("按当前零售价估算的库存货值", report)
        self.assertIn("非采购成本", report)
        self.assertNotIn("资金占用", report)


if __name__ == "__main__":
    unittest.main()
