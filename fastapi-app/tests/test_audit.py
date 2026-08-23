"""操作审计测试（SQLite 内存，不触网络）。

覆盖 roadmap 改进项 4 的核心不变量：
  - 敏感操作成功后审计记录落库（操作者/动作/目标/明细）
  - 审计写入失败绝不阻塞业务（best-effort + 日志兜底）
  - 状态机拒绝的变更不留审计噪声
  - 归属字段（operator_role/operator_id）取自当前操作者"""
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise

from api.orders import update_status as order_update_status
from api.user import UserCreate, reset_password
from common.exception_handler import ConflictException
from models import Address, AuditLog, Goods, Orders, User


ADMIN = {"user_id": 1, "username": "admin", "role": "管理员"}
USER = {"user_id": 2, "username": "buyer", "role": "用户"}


class _FakeClient:
    host = "10.0.0.8"


class FakeRequest:
    client = _FakeClient()


class AuditLogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=ADMIN["user_id"], username="admin", role="管理员")
        await User.create(id=USER["user_id"], username="buyer", role="用户")
        self.goods = await Goods.create(
            id=1, name="测试蛋糕", price=Decimal("98.00"), num=10, unit="份"
        )
        self.address = await Address.create(
            id=1, user_id=USER["user_id"], name="买家", phone="13800000000", address="测试地址",
        )
        self.order = await Orders.create(
            id=1, user_id=USER["user_id"], goods_id=1, address_id=1, num=1,
            order_no="A1", time="2026-08-21 10:00:00", status="待发货",
            total_price=Decimal("98"),
        )

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_reset_password_writes_audit_with_operator_and_ip(self):
        await reset_password(
            USER["user_id"], UserCreate(username="buyer", password="strong-pass-9"),
            ADMIN, FakeRequest(),
        )
        log = await AuditLog.all().first()
        self.assertEqual(log.action, "user.reset_password")
        self.assertEqual(log.operator_role, "管理员")
        self.assertEqual(log.operator_id, ADMIN["user_id"])
        self.assertEqual(log.target_type, "user")
        self.assertEqual(log.target_id, USER["user_id"])
        self.assertEqual(log.ip, "10.0.0.8")

    async def test_audit_failure_does_not_block_business(self):
        """审计写入异常时业务必须已成功——审计是 best-effort，不是事务参与者。"""
        with patch.object(
            AuditLog, "create", new=AsyncMock(side_effect=RuntimeError("audit table gone")),
        ):
            await reset_password(
                USER["user_id"], UserCreate(username="buyer", password="strong-pass-9"),
                ADMIN,
            )
        user = await User.get(id=USER["user_id"])
        self.assertTrue(user.must_change_password, "密码重置业务不应被审计失败回滚")
        self.assertEqual(user.token_version, 1, "token_version 递增证明 UPDATE 已生效")

    async def test_order_status_change_audited_with_transition(self):
        await order_update_status(1, "已发货", ADMIN, FakeRequest())
        log = await AuditLog.all().first()
        self.assertEqual(log.action, "order.status_change")
        self.assertEqual(log.detail["from"], "待发货")
        self.assertEqual(log.detail["to"], "已发货")

    async def test_rejected_transition_writes_no_audit(self):
        with self.assertRaises(ConflictException):
            await order_update_status(1, "已评价", USER)  # 非法流转
        self.assertEqual(await AuditLog.all().count(), 0, "被拒绝的变更不留审计噪声")

    async def test_direct_call_without_request_records_null_ip(self):
        await order_update_status(1, "已发货", ADMIN)  # 无 Request（测试/内部调用）
        log = await AuditLog.all().first()
        self.assertIsNone(log.ip)
        self.assertEqual(log.action, "order.status_change")


if __name__ == "__main__":
    unittest.main()
