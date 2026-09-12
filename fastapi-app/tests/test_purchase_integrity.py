import unittest
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from tortoise import Tortoise
from api.orders import add, select, OrdersCreatePydantic
from api.cart import checkout, CartCheckoutPydantic
from agents.tools.order.repository import get_order_status
from common.exception_handler import ConflictException, NotFoundException
from models import User, Goods, Address, Cart, Orders, WalletTransaction, PurchaseRequest

USER={"user_id":7,"role":"用户"}
class PurchaseIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:",modules={"models":["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=7,username="buyer",balance=1000)
        self.goods=await Goods.create(name="蛋糕",price=60,num=5,specs="6寸/8寸")
        self.address=await Address.create(user_id=7,name="甲",phone="13800000000",address="原地址")
    async def asyncTearDown(self):
        await Tortoise.close_connections()
    def payload(self, **changes):
        values=dict(request_id="intent_0001",goodsId=self.goods.id,addressId=self.address.id,num=1,spec="8寸")
        values.update(changes)
        return OrdersCreatePydantic(**values)
    async def test_duplicate_intent_debits_and_decrements_once(self):
        first=await add(self.payload(),USER)
        again=await add(self.payload(),USER)
        self.assertEqual(first.data,again.data)
        self.assertEqual(await Orders.all().count(),1)
        self.assertEqual((await User.get(id=7)).balance,Decimal(940))
        self.assertEqual((await Goods.get(id=self.goods.id)).num,4)
    async def test_same_key_changed_payload_rejected(self):
        await add(self.payload(),USER)
        with self.assertRaises(ConflictException):
            await add(self.payload(num=2),USER)
        self.assertEqual(await WalletTransaction.all().count(),1)
    async def test_address_and_spec_are_immutable_in_api_and_agent(self):
        await add(self.payload(),USER)
        await Address.filter(id=self.address.id).update(name="乙",address="新地址")
        await Goods.filter(id=self.goods.id).update(specs="10寸",price=90)
        page=(await select(current_user=USER)).data
        self.assertEqual(page["list"][0]["aAddress"],"原地址")
        self.assertEqual(page["list"][0]["spec"],"8寸")
        order=await Orders.all().first()
        self.assertIn("原地址",await get_order_status(7,order_id=order.id))
    async def test_free_order_has_no_money_transfer(self):
        await Goods.filter(id=self.goods.id).update(price=0)
        await add(self.payload(),USER)
        self.assertEqual(await WalletTransaction.all().count(),0)
        self.assertEqual((await Orders.all().first()).total_price,Decimal(0))
        self.assertEqual((await Goods.get(id=self.goods.id)).num,4)
    async def test_checkout_replay_and_consumed_rows(self):
        row=await Cart.create(user_id=7,goods_id=self.goods.id,num=2,spec="6寸")
        p=CartCheckoutPydantic(request_id="checkout_001",ids=[row.id],addressId=self.address.id)
        first=await checkout(p,USER)
        self.assertEqual((await checkout(p,USER)).data,first.data)
        with self.assertRaises(NotFoundException):
            await checkout(p.model_copy(update={"request_id":"checkout_002"}),USER)
        self.assertEqual(await Orders.all().count(),1)
    async def test_specs_share_stock_and_cannot_oversell_in_checkout(self):
        rows=[await Cart.create(user_id=7,goods_id=self.goods.id,num=3,spec=s) for s in ["6寸","8寸"]]
        with self.assertRaises(ConflictException):
            await checkout(CartCheckoutPydantic(request_id="checkout_001",ids=[r.id for r in rows],addressId=self.address.id),USER)
        self.assertEqual(await Orders.all().count(),0)
        self.assertEqual(await Cart.all().count(),2)
    async def test_request_record_failure_rolls_back_money_stock_and_orders(self):
        with patch("domain.purchase.PurchaseRequest.create",AsyncMock(side_effect=RuntimeError("fail"))):
            with self.assertRaises(RuntimeError):
                await add(self.payload(),USER)
        self.assertEqual(await Orders.all().count(),0)
        self.assertEqual(await WalletTransaction.all().count(),0)
        self.assertEqual((await User.get(id=7)).balance,Decimal(1000))
        self.assertEqual((await Goods.get(id=self.goods.id)).num,5)
