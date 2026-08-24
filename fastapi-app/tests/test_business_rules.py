"""业务写路径集成测试（带真实数据库，SQLite 内存）。

覆盖审查报告指出的最有价值业务不变量：
  - 下单原子扣库存 + 成交价快照
  - 订单状态机拒绝非法流转
  - 取消订单回补库存且不二次回补
  - 一单一评防重复
  - 改价后历史订单金额不变（total_price 快照）
  - 统计口径排除已取消订单

局限说明：SQLite 上 select_for_update 是静默 no-op（方言不支持行锁），
行锁并发语义（防超卖）在 MySQL 生产环境才生效，本测试只验证事务内的
业务逻辑正确性，不验证锁竞争。
"""
import unittest
from decimal import Decimal

from tortoise import Tortoise

from api.orders import (
    ORDER_CANCELLED,
    ORDER_PENDING,
    ORDER_PENDING_REVIEW,
    ORDER_REVIEWED,
    ORDER_SHIPPED,
    OrdersCreatePydantic,
    add as order_add,
    delete as order_delete,
    update_status as order_update_status,
)
from api.reviews import ReviewCreatePydantic, add as review_add
from api.stats import _sum_revenue
from common.exception_handler import CustomException
from models import Address, Goods, Orders, Review, User


ADMIN = {"user_id": 1, "username": "admin", "role": "管理员"}
USER = {"user_id": 2, "username": "buyer", "role": "用户"}


class BusinessRulesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=USER["user_id"], username="buyer", role="用户", balance=Decimal("10000.00"))
        await User.create(id=99, username="other", role="用户")
        self.address = await Address.create(
            id=1, user_id=USER["user_id"], name="买家", phone="13800000000", address="测试地址",
        )
        self.other_address = await Address.create(
            id=2, user_id=99, name="他人", phone="13900000000", address="他人地址",
        )
        self.goods = await Goods.create(
            id=1, name="测试蛋糕", price=Decimal("98.00"), num=10, unit="份"
        )

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def _place_order(self, num: int = 1) -> int:
        payload = OrdersCreatePydantic(goodsId=1, addressId=self.address.id, num=num)
        await order_add(payload, USER)
        order = await Orders.all().order_by("-id").first()
        return order.id

    async def test_order_create_decrements_stock_and_snapshots_price(self):
        await self._place_order(num=3)
        goods = await Goods.get(id=1)
        order = await Orders.all().order_by("-id").first()
        self.assertEqual(goods.num, 7, "下单必须原子扣减库存")
        self.assertEqual(order.total_price, Decimal("294.00"), "快照 = 单价 × 数量")
        self.assertEqual(order.status, ORDER_PENDING)

    async def test_order_rejects_oversell_and_missing_goods(self):
        with self.assertRaises(CustomException):
            await order_add(OrdersCreatePydantic(goodsId=1, addressId=self.address.id, num=11), USER)
        with self.assertRaises(CustomException):
            await order_add(OrdersCreatePydantic(goodsId=999, addressId=self.address.id, num=1), USER)
        self.assertEqual((await Goods.get(id=1)).num, 10, "失败的下单不得扣库存")

    async def test_order_requires_address_owned_by_current_customer(self):
        with self.assertRaises(CustomException):
            await order_add(OrdersCreatePydantic(goodsId=1, num=1), USER)
        with self.assertRaises(CustomException):
            await order_add(
                OrdersCreatePydantic(goodsId=1, addressId=self.other_address.id, num=1),
                USER,
            )
        self.assertEqual(await Orders.all().count(), 0)
        self.assertEqual((await Goods.get(id=1)).num, 10)

    async def test_state_machine_rejects_illegal_transitions(self):
        order_id = await self._place_order()
        # 用户不能发货（管理员专属）、不能凭空推进到已评价
        with self.assertRaises(CustomException):
            await order_update_status(order_id, ORDER_SHIPPED, USER)
        with self.assertRaises(CustomException):
            await order_update_status(order_id, ORDER_REVIEWED, USER)
        # 合法链路：管理员发货 → 用户确认收货(待评价)
        await order_update_status(order_id, ORDER_SHIPPED, ADMIN)
        await order_update_status(order_id, ORDER_PENDING_REVIEW, USER)
        self.assertEqual((await Orders.get(id=order_id)).status, ORDER_PENDING_REVIEW)

    async def test_cancel_restores_stock_exactly_once(self):
        order_id = await self._place_order(num=2)
        await order_update_status(order_id, ORDER_CANCELLED, USER)
        self.assertEqual((await Goods.get(id=1)).num, 10, "取消必须回补库存")
        # 已取消是终态：再次流转被拒 → 不可能二次回补
        with self.assertRaises(CustomException):
            await order_update_status(order_id, ORDER_CANCELLED, USER)
        self.assertEqual((await Goods.get(id=1)).num, 10, "终态拦截保证无二次回补")

    async def test_legacy_delete_cancels_without_erasing_audit_record(self):
        order_id = await self._place_order(num=2)
        await order_delete(order_id, USER)
        order = await Orders.get(id=order_id)
        self.assertEqual(order.status, ORDER_CANCELLED)
        self.assertEqual((await Goods.get(id=1)).num, 10)

        # 重复请求幂等：订单仍在，库存不会二次回补。
        await order_delete(order_id, USER)
        self.assertEqual(await Orders.filter(id=order_id).count(), 1)
        self.assertEqual((await Goods.get(id=1)).num, 10)

    async def test_legacy_delete_rejects_completed_order(self):
        order_id = await self._place_order()
        await order_update_status(order_id, ORDER_SHIPPED, ADMIN)
        await order_update_status(order_id, ORDER_PENDING_REVIEW, USER)
        with self.assertRaises(CustomException):
            await order_delete(order_id, USER)
        self.assertTrue(await Orders.filter(id=order_id).exists())

    async def test_review_once_per_order_and_requires_pending_review_status(self):
        order_id = await self._place_order()
        # 待发货状态不允许评价
        with self.assertRaises(CustomException):
            await review_add(ReviewCreatePydantic(rating=5, content="好", orderId=order_id), USER)
        await order_update_status(order_id, ORDER_SHIPPED, ADMIN)
        await order_update_status(order_id, ORDER_PENDING_REVIEW, USER)
        await review_add(ReviewCreatePydantic(rating=5, content="好", orderId=order_id), USER)
        # 同一订单第二次评价被拒
        with self.assertRaises(CustomException):
            await review_add(ReviewCreatePydantic(rating=4, content="再来", orderId=order_id), USER)
        self.assertEqual(await Review.all().count(), 1)
        self.assertEqual((await Orders.get(id=order_id)).status, ORDER_REVIEWED)

    async def test_review_cannot_be_attached_to_a_different_product(self):
        other_goods = await Goods.create(
            id=2, name="未购买蛋糕", price=Decimal("88.00"), num=5, unit="份",
        )
        order_id = await self._place_order()
        await order_update_status(order_id, ORDER_SHIPPED, ADMIN)
        await order_update_status(order_id, ORDER_PENDING_REVIEW, USER)

        with self.assertRaises(CustomException):
            await review_add(
                ReviewCreatePydantic(
                    rating=5, content="试图跨商品评价", orderId=order_id, goodsId=other_goods.id,
                ),
                USER,
            )
        self.assertEqual(await Review.all().count(), 0)
        self.assertEqual((await Orders.get(id=order_id)).status, ORDER_PENDING_REVIEW)

    async def test_price_change_does_not_rewrite_history(self):
        """改价后历史订单金额不变——total_price 快照存在的根本理由。"""
        await self._place_order(num=2)  # 98 × 2 = 196
        self.goods.price = Decimal("199.00")
        await self.goods.save(update_fields=["price"])
        order = await Orders.all().order_by("-id").first()
        self.assertEqual(order.total_price, Decimal("196.00"), "历史订单金额不随改价漂移")

    async def test_revenue_aggregation_excludes_cancelled(self):
        await self._place_order(num=1)          # 98
        order_id2 = await self._place_order(num=2)  # 196
        await self._place_order(num=1)          # 98 → 合计 392
        await order_update_status(order_id2, ORDER_CANCELLED, USER)
        revenue = await _sum_revenue()
        self.assertEqual(revenue, 196.0, "已取消订单不计入销售额")
        user_spent = await _sum_revenue(user_id=USER["user_id"])
        self.assertEqual(user_spent, 196.0)

    async def test_order_no_is_unique(self):
        ids = {(await Orders.get(id=await self._place_order())).order_no for _ in range(5)}
        self.assertEqual(len(ids), 5, "连续生成的订单号不得重复")


if __name__ == "__main__":
    unittest.main()
