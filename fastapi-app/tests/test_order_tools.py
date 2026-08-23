import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agents.tools.order.repository import ORDER_CANCELLED, cancel_order


class AsyncTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class LockedQuery:
    def __init__(self, row):
        self.row = row

    def select_for_update(self):
        return self

    async def first(self):
        return self.row


class CancelOrderRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_marks_order_and_restores_inventory_atomically(self):
        order = SimpleNamespace(
            id=9,
            order_no="202608130001",
            status="待发货",
            goods_id=3,
            num=2,
            save=AsyncMock(),
        )
        goods = SimpleNamespace(name="草莓蛋糕", num=5, save=AsyncMock())

        notify = AsyncMock()
        with patch(
            "agents.tools.order.repository.in_transaction",
            return_value=AsyncTransaction(),
        ), patch(
            "agents.tools.order.repository.Orders.filter",
            return_value=LockedQuery(order),
        ), patch(
            "agents.tools.order.repository.Goods.filter",
            return_value=LockedQuery(goods),
        ), patch(
            "agents.tools.order.repository.notify_order_event", notify,
        ):
            result = await cancel_order(user_id=7, order_no="202608130001")

        self.assertEqual(order.status, ORDER_CANCELLED)
        order.save.assert_awaited_once_with(update_fields=["status"])
        self.assertEqual(goods.num, 7)
        goods.save.assert_awaited_once_with(update_fields=["num"])
        self.assertIn("库存已恢复", result)
        # 取消成功必须伴随买家通知（同事务）
        notify.assert_awaited_once_with(order, goods.name)

    async def test_repeated_cancel_does_not_restore_inventory_twice(self):
        order = SimpleNamespace(
            id=9,
            order_no="202608130001",
            status=ORDER_CANCELLED,
            goods_id=3,
            num=2,
            save=AsyncMock(),
        )
        goods_filter = MagicMock()

        with patch(
            "agents.tools.order.repository.in_transaction",
            return_value=AsyncTransaction(),
        ), patch(
            "agents.tools.order.repository.Orders.filter",
            return_value=LockedQuery(order),
        ), patch("agents.tools.order.repository.Goods.filter", goods_filter), patch(
            "agents.tools.order.repository.notify_order_event", AsyncMock(),
        ):
            result = await cancel_order(user_id=7, order_no="202608130001")

        goods_filter.assert_not_called()
        order.save.assert_not_awaited()
        self.assertIn("已经取消", result)

    async def test_missing_goods_keeps_order_active(self):
        order = SimpleNamespace(
            id=9,
            order_no="202608130001",
            status="待发货",
            goods_id=3,
            num=2,
            save=AsyncMock(),
        )

        with patch(
            "agents.tools.order.repository.in_transaction",
            return_value=AsyncTransaction(),
        ), patch(
            "agents.tools.order.repository.Orders.filter",
            return_value=LockedQuery(order),
        ), patch(
            "agents.tools.order.repository.Goods.filter",
            return_value=LockedQuery(None),
        ), patch(
            "agents.tools.order.repository.notify_order_event", AsyncMock(),
        ):
            result = await cancel_order(user_id=7, order_no="202608130001")

        self.assertEqual(order.status, "待发货")
        order.save.assert_not_awaited()
        self.assertIn("避免库存不一致", result)


if __name__ == "__main__":
    unittest.main()
