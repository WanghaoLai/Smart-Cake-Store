"""购物车测试（SQLite 内存）。

覆盖核心不变量：
  - 加购合并/库存上限/归属隔离
  - 结算事务原子性：订单创建、库存扣减、余额支付、流水快照、购物车清理同成败
  - 库存不足/余额不足/地址不属于本人/混入他人条目 id 时整体回滚
"""
import unittest
from decimal import Decimal

from tortoise import Tortoise

from api.cart import (
    CartAddPydantic,
    CartCheckoutPydantic,
    CartIdsPydantic,
    CartSelectPydantic,
    CartUpdatePydantic,
    add as cart_add,
    checkout,
    count_items,
    list_items,
    remove_batch,
    remove_one,
    select_all,
    select_one,
    update_num,
)
from common.exception_handler import ConflictException, ForbiddenException, NotFoundException
from models import Address, Cart, Goods, Orders, User, WalletTransaction


USER = {"user_id": 2, "username": "buyer", "role": "用户"}
OTHER = {"user_id": 99, "username": "other", "role": "用户"}


class CartTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=USER["user_id"], username="buyer", role="用户", balance=Decimal("10000.00"))
        await User.create(id=OTHER["user_id"], username="other", role="用户", balance=Decimal("0.00"))
        self.address = await Address.create(
            id=1, user_id=USER["user_id"], name="买家", phone="13800000000", address="测试地址",
        )
        self.g1 = await Goods.create(id=1, name="草莓蛋糕", price=Decimal("98.00"), num=10, unit="份")
        self.g2 = await Goods.create(id=2, name="巧克力蛋糕", price=Decimal("128.00"), num=5, unit="份")

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def _add(self, goods_id: int, num: int, user=USER):
        return await cart_add(CartAddPydantic(goodsId=goods_id, num=num), user)

    async def test_add_merges_same_goods_and_caps_at_stock(self):
        await self._add(1, 2)
        await self._add(1, 3)
        self.assertEqual(await Cart.all().count(), 1)
        self.assertEqual((await Cart.all().first()).num, 5)
        # 累加后超出库存 → 拒绝，原数量不变
        with self.assertRaises(ConflictException):
            await self._add(1, 6)
        self.assertEqual((await Cart.all().first()).num, 5)

    async def test_add_unknown_goods_rejected(self):
        with self.assertRaises(NotFoundException):
            await self._add(999, 1)

    async def test_list_and_count_are_owner_scoped(self):
        await self._add(1, 2)
        await self._add(2, 3, user=OTHER)
        mine = (await list_items(USER)).data
        self.assertEqual(mine["total"], 1)
        self.assertEqual(mine["list"][0]["goodsName"], "草莓蛋糕")
        self.assertEqual(mine["list"][0]["stock"], 10)
        self.assertEqual((await count_items(USER)).data["count"], 2)
        self.assertEqual((await count_items(OTHER)).data["count"], 3)

    async def test_update_num_validates_stock(self):
        await self._add(1, 2)
        row = await Cart.all().first()
        await update_num(row.id, CartUpdatePydantic(num=4), USER)
        self.assertEqual((await Cart.all().first()).num, 4)
        with self.assertRaises(ConflictException):
            await update_num(row.id, CartUpdatePydantic(num=11), USER)

    async def test_remove_and_batch_remove_are_owner_scoped(self):
        await self._add(1, 1)
        await self._add(2, 1)
        other_row = await Cart.create(user_id=OTHER["user_id"], goods_id=2, num=1)
        r1, r2 = await Cart.filter(user_id=USER["user_id"]).order_by("id")

        await remove_one(r1.id, USER)
        self.assertEqual(await Cart.filter(user_id=USER["user_id"]).count(), 1)

        # 批量删除混入他人条目：只删自己的
        result = (await remove_batch(CartIdsPydantic(ids=[r2.id, other_row.id]), USER)).data
        self.assertEqual(result["deleted"], 1)
        self.assertTrue(await Cart.filter(id=other_row.id).exists())

    async def test_select_one_and_select_all(self):
        await self._add(1, 1)
        await self._add(2, 1)
        r1 = await Cart.filter(goods_id=1).first()

        await select_one(r1.id, CartSelectPydantic(selected=False), USER)
        self.assertFalse((await Cart.get(id=r1.id)).selected)

        await select_all(CartSelectPydantic(selected=False), USER)
        self.assertEqual(await Cart.filter(user_id=USER["user_id"], selected=False).count(), 2)
        await select_all(CartSelectPydantic(selected=True), USER)
        self.assertEqual(await Cart.filter(user_id=USER["user_id"], selected=True).count(), 2)

    async def test_checkout_creates_orders_and_clears_cart_atomically(self):
        await self._add(1, 2)   # 98 × 2 = 196
        await self._add(2, 1)   # 128 × 1 = 128 → 合计 324
        ids = [r.id for r in await Cart.filter(user_id=USER["user_id"])]

        result = (await checkout(CartCheckoutPydantic(ids=ids, addressId=1), USER)).data
        self.assertEqual(Decimal(str(result["total"])), Decimal("324.00"))
        self.assertEqual(len(result["order_nos"]), 2)

        self.assertEqual(await Cart.filter(user_id=USER["user_id"]).count(), 0)
        self.assertEqual(await Orders.filter(user_id=USER["user_id"]).count(), 2)
        # 库存扣减
        self.assertEqual((await Goods.get(id=1)).num, 8)
        self.assertEqual((await Goods.get(id=2)).num, 4)
        # 余额一次性扣总金额，流水逐笔回填滚动快照
        self.assertEqual((await User.get(id=USER["user_id"])).balance, Decimal("9676.00"))
        payments = await WalletTransaction.filter(user_id=USER["user_id"], type="payment").order_by("id")
        self.assertEqual(len(payments), 2)
        self.assertEqual([p.balance_after for p in payments][-1], Decimal("9676.00"))

    async def test_checkout_insufficient_stock_rolls_back_everything(self):
        await self._add(1, 2)
        await self._add(2, 1)
        await Goods.filter(id=2).update(num=0)  # 结算时第二个商品库存不足
        ids = [r.id for r in await Cart.filter(user_id=USER["user_id"])]

        with self.assertRaises(ConflictException):
            await checkout(CartCheckoutPydantic(ids=ids, addressId=1), USER)
        # 整体回滚：无订单、库存未动、购物车未清
        self.assertEqual(await Orders.all().count(), 0)
        self.assertEqual((await Goods.get(id=1)).num, 10)
        self.assertEqual(await Cart.filter(user_id=USER["user_id"]).count(), 2)

    async def test_checkout_insufficient_balance_rolls_back(self):
        await User.filter(id=USER["user_id"]).update(balance=Decimal("100.00"))
        await self._add(1, 2)  # 需 196 > 100
        ids = [r.id for r in await Cart.filter(user_id=USER["user_id"])]
        with self.assertRaises(ConflictException):
            await checkout(CartCheckoutPydantic(ids=ids, addressId=1), USER)
        self.assertEqual(await Orders.all().count(), 0)
        self.assertEqual(await Cart.filter(user_id=USER["user_id"]).count(), 1)

    async def test_checkout_rejects_foreign_address_and_foreign_ids(self):
        await self._add(1, 1)
        ids = [r.id for r in await Cart.filter(user_id=USER["user_id"])]
        with self.assertRaises(ForbiddenException):
            await checkout(CartCheckoutPydantic(ids=ids, addressId=999), USER)
        # 混入不存在的条目 id → 整体拒绝
        with self.assertRaises(NotFoundException):
            await checkout(CartCheckoutPydantic(ids=ids + [99999], addressId=1), USER)


if __name__ == "__main__":
    unittest.main()
