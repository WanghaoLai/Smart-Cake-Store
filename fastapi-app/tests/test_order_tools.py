import uuid
import unittest
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from tortoise import Tortoise
from models import User, Goods, Address, Orders, WalletTransaction, AuditLog, Notification
from api.orders import add, delete, OrdersCreatePydantic
from agents.tools.order.repository import cancel_order

USER = {"user_id":7,"role":"用户"}
class CancelOrderRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:",modules={"models":["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=7,username="buyer",balance=100)
        self.goods = await Goods.create(name="蛋糕",price=60,num=5)
        self.address = await Address.create(user_id=7,address="原地址")
        await add(OrdersCreatePydantic(request_id=uuid.uuid4().hex, goodsId=self.goods.id,addressId=self.address.id,num=1),USER)
        self.order = await Orders.all().first()
    async def asyncTearDown(self):
        await Tortoise.close_connections()
    async def test_agent_and_api_refund_once(self):
        result = await cancel_order(7,order_id=self.order.id)
        self.assertIn("已成功取消", result)
        await delete(self.order.id,USER)
        self.assertEqual((await User.get(id=7)).balance,Decimal(100))
        self.assertEqual((await Goods.get(id=self.goods.id)).num,5)
        self.assertEqual(await WalletTransaction.filter(type="refund").count(),1)
        self.assertEqual(await AuditLog.all().count(),1)
        self.assertEqual(await Notification.all().count(),1)
    async def test_historical_cancel_refunds_without_restoring_twice(self):
        await Orders.filter(id=self.order.id).update(status="已取消")
        await Goods.filter(id=self.goods.id).update(num=5)
        await cancel_order(7,order_id=self.order.id)
        await cancel_order(7,order_id=self.order.id)
        self.assertEqual((await User.get(id=7)).balance,Decimal(100))
        self.assertEqual((await Goods.get(id=self.goods.id)).num,5)
    async def test_refund_failure_rolls_back_all_changes(self):
        with patch("domain.order_cancellation.WalletTransaction.create",AsyncMock(side_effect=RuntimeError("fail"))):
            with self.assertRaises(RuntimeError):
                await cancel_order(7,order_id=self.order.id)
        self.assertEqual((await Orders.get(id=self.order.id)).status,"待发货")
        self.assertEqual((await Goods.get(id=self.goods.id)).num,4)
        self.assertEqual((await User.get(id=7)).balance,Decimal(40))
        self.assertEqual(await Notification.all().count(),0)
    async def test_other_user_cannot_cancel(self):
        self.assertIn("未找到",await cancel_order(8,order_id=self.order.id))
        self.assertEqual((await Orders.get(id=self.order.id)).status,"待发货")
