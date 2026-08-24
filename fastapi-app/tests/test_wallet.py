import unittest
from decimal import Decimal

from tortoise import Tortoise

from api.orders import OrdersCreatePydantic, add as order_add, update_status
from api.wallet import RechargeRequest, recharge, transactions
from common.exception_handler import CustomException
from domain.order_status import ORDER_CANCELLED
from models import Address, Goods, Orders, User, WalletTransaction


USER = {"user_id": 7, "username": "wallet-user", "role": "用户"}


class WalletTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=7, username="wallet-user", role="用户", balance=Decimal("0.00"))
        self.address = await Address.create(user_id=7, name="用户", phone="13800000000", address="测试地址")
        await Goods.create(id=1, name="余额蛋糕", price=Decimal("60.00"), num=5, unit="个")

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_recharge_is_idempotent(self):
        payload = RechargeRequest(amount=Decimal("100.00"), payment_method="alipay", request_id="wallet_request_0001")
        await recharge(payload, USER)
        await recharge(payload, USER)
        self.assertEqual((await User.get(id=7)).balance, Decimal("100.00"))
        self.assertEqual(await WalletTransaction.filter(type="recharge").count(), 1)

    async def test_insufficient_balance_does_not_change_stock(self):
        with self.assertRaises(CustomException):
            await order_add(OrdersCreatePydantic(goodsId=1, addressId=self.address.id, num=1), USER)
        self.assertEqual((await Goods.get(id=1)).num, 5)
        self.assertEqual(await Orders.all().count(), 0)

    async def test_payment_and_cancel_refund_are_atomic(self):
        await recharge(RechargeRequest(amount=Decimal("100.00"), payment_method="wechat", request_id="wallet_request_0002"), USER)
        await order_add(OrdersCreatePydantic(goodsId=1, addressId=self.address.id, num=1), USER)
        order = await Orders.all().first()
        self.assertEqual((await User.get(id=7)).balance, Decimal("40.00"))
        await update_status(order.id, ORDER_CANCELLED, USER)
        self.assertEqual((await User.get(id=7)).balance, Decimal("100.00"))
        self.assertEqual(await WalletTransaction.filter(order_id=order.id, type="refund").count(), 1)

    async def test_transaction_query_is_user_scoped(self):
        await recharge(RechargeRequest(amount=Decimal("20.00"), payment_method="bank_card", request_id="wallet_request_0003"), USER)
        result = await transactions(current_user=USER)
        self.assertEqual(result.data["total"], 1)
        self.assertEqual(result.data["list"][0]["type"], "recharge")


if __name__ == "__main__":
    unittest.main()
