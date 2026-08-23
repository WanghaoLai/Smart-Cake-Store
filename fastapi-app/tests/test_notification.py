"""订单站内通知测试（SQLite 内存）。

覆盖 roadmap 改进项 6 的核心不变量：
  - 发货/取消在状态变更事务内产生通知（API 路径与 Agent 路径一致）
  - 用户自己确认收货（待评价）不打扰
  - 状态机拒绝时无通知（事务回滚）
  - 未读数与全部已读按 角色+user_id 归属隔离"""
import unittest
from decimal import Decimal

from tortoise import Tortoise

from agents.tools.order import repository as order_repository
from api.notification import list_notifications, read_all, unread_count
from api.orders import (
    OrdersCreatePydantic,
    add as order_add,
    delete as order_delete,
    update_status as order_update_status,
)
from common.exception_handler import ConflictException
from models import Address, Goods, Notification, Orders, User


ADMIN = {"user_id": 1, "username": "admin", "role": "管理员"}
USER = {"user_id": 2, "username": "buyer", "role": "用户"}
OTHER = {"user_id": 99, "username": "other", "role": "用户"}


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=ADMIN["user_id"], username="admin", role="管理员")
        await User.create(id=USER["user_id"], username="buyer", role="用户")
        await User.create(id=OTHER["user_id"], username="other", role="用户")
        self.address = await Address.create(
            id=1, user_id=USER["user_id"], name="买家", phone="13800000000", address="测试地址",
        )
        self.goods = await Goods.create(
            id=1, name="草莓蛋糕", price=Decimal("98.00"), num=10, unit="份"
        )

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def _place_order(self, num: int = 1) -> Orders:
        await order_add(OrdersCreatePydantic(goodsId=1, num=num, addressId=self.address.id), USER)
        return await Orders.all().order_by("-id").first()

    async def test_shipping_writes_notification_to_buyer(self):
        order = await self._place_order()
        await order_update_status(order.id, "已发货", ADMIN)
        n = await Notification.all().first()
        self.assertEqual(n.user_id, USER["user_id"])
        self.assertEqual(n.owner_role, "用户")
        self.assertEqual(n.type, "order.shipped")
        self.assertFalse(n.is_read)
        self.assertIn("草莓蛋糕", n.content)
        self.assertIn(order.order_no, n.content)

    async def test_cancel_via_api_writes_notification(self):
        order = await self._place_order()
        await order_update_status(order.id, "已取消", USER)
        n = await Notification.all().first()
        self.assertEqual(n.type, "order.cancelled")

    async def test_cancel_via_agent_writes_notification(self):
        order = await self._place_order()
        result = await order_repository.cancel_order(user_id=USER["user_id"], order_id=order.id)
        self.assertIn("已成功取消", result)
        n = await Notification.all().first()
        self.assertEqual(n.type, "order.cancelled")
        self.assertEqual(n.user_id, USER["user_id"])

    async def test_soft_cancel_via_delete_writes_notification(self):
        """历史 DELETE 端点现为软取消语义，买家可感知性必须与 update_status 一致。"""
        order = await self._place_order()
        await order_delete(order.id, USER)
        n = await Notification.all().first()
        self.assertEqual((await Orders.get(id=order.id)).status, "已取消")
        self.assertEqual(n.type, "order.cancelled")
        self.assertIn(order.order_no, n.content)

    async def test_repeated_soft_cancel_notifies_only_once(self):
        """幂等重复取消不重复通知。"""
        order = await self._place_order()
        await order_delete(order.id, USER)
        await order_delete(order.id, USER)
        self.assertEqual(await Notification.all().count(), 1)

    async def test_user_confirm_receipt_is_not_notified(self):
        """确认收货是用户自己的操作，不需要平台通知自己。"""
        order = await self._place_order()
        await order_update_status(order.id, "已发货", ADMIN)
        await order_update_status(order.id, "待评价", USER)
        self.assertEqual(await Notification.all().count(), 1, "只应有发货一条")

    async def test_rejected_transition_writes_no_notification(self):
        order = await self._place_order()
        with self.assertRaises(ConflictException):
            await order_update_status(order.id, "已评价", USER)
        self.assertEqual(await Notification.all().count(), 0)

    async def test_unread_count_and_read_all_are_owner_scoped(self):
        order = await self._place_order()
        await order_update_status(order.id, "已发货", ADMIN)

        # 本人可见 1 条未读；无关用户不可见（归属隔离）
        self.assertEqual((await unread_count(USER)).data["count"], 1)
        self.assertEqual((await unread_count(OTHER)).data["count"], 0)

        await read_all(USER)
        self.assertEqual((await unread_count(USER)).data["count"], 0)
        self.assertEqual(await Notification.filter(is_read=False).count(), 0)

    async def test_list_returns_owner_notifications_desc(self):
        o1 = await self._place_order()
        o2 = await self._place_order()
        await order_update_status(o1.id, "已发货", ADMIN)
        await order_update_status(o2.id, "已发货", ADMIN)
        page = (await list_notifications(pageNum=1, pageSize=10, current_user=USER)).data
        self.assertEqual(page["total"], 2)
        titles = [item["title"] for item in page["list"]]
        self.assertEqual(titles, ["订单已发货", "订单已发货"])
        # 他人的列表为空
        other_page = (await list_notifications(pageNum=1, pageSize=10, current_user=OTHER)).data
        self.assertEqual(other_page["total"], 0)


if __name__ == "__main__":
    unittest.main()
