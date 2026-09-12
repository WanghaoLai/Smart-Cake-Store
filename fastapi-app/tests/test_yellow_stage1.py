"""第一阶段：认证并发、限流回收和请求输入边界。"""
import asyncio
import threading
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from tortoise import Tortoise

from api.admin import AdminUpdate
from api.goods import GoodsUpdate
from api.user import PasswordResetRequest, UserUpdate, reset_password
from common.auth import async_hash_password
from common.rate_limit import SlidingWindowRateLimiter
from models import User


class PasswordWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_hashing_runs_off_event_loop(self):
        started = threading.Event()
        release = threading.Event()

        def slow_hash(*_args, **_kwargs):
            started.set()
            release.wait(timeout=2)
            return "hash"

        with patch("common.auth.hash_password", side_effect=slow_hash):
            task = asyncio.create_task(async_hash_password("Safe-password-2026"))
            await asyncio.to_thread(started.wait, 1)
            # 如果 bcrypt 仍在事件循环中，这个调度点无法执行。
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            release.set()
            self.assertEqual(await task, "hash")


class RateLimiterCleanupTests(unittest.TestCase):
    def test_expired_subjects_are_pruned(self):
        limiter = SlidingWindowRateLimiter(2, 10)
        limiter.allow("account:a", now=0)
        limiter.allow("account:b", now=1)
        self.assertEqual(limiter.tracked_keys, 2)
        limiter.prune(now=12)
        self.assertEqual(limiter.tracked_keys, 0)

    def test_account_key_does_not_need_client_ip(self):
        account = SlidingWindowRateLimiter(1, 60)
        self.assertTrue(account.allow("用户:alice", now=0))
        self.assertFalse(account.allow("用户:alice", now=1))


class CredentialGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=1, username="alice", password="old", token_version=4)

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_each_reset_atomically_advances_generation(self):
        operator = {"user_id": 9, "username": "root", "role": "管理员"}
        with patch("api.user.record_audit_required"):
            await reset_password(1, PasswordResetRequest(password="Safe-reset-2026-A"), operator)
            await reset_password(1, PasswordResetRequest(password="Safe-reset-2026-B"), operator)
        user = await User.get(id=1)
        self.assertEqual(user.token_version, 6)


class RequestBoundaryTests(unittest.TestCase):
    def test_nullable_database_core_fields_reject_explicit_null(self):
        for payload in (
            {"id": 1, "name": None},
            {"id": 1, "price": None},
            {"id": 1, "num": None},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                GoodsUpdate(**payload)

    def test_account_update_rejects_null_credentials_and_blank_username(self):
        for schema in (UserUpdate, AdminUpdate):
            for values in ({"id": 1, "username": None}, {"id": 1, "password": None},
                           {"id": 1, "username": "   "}):
                with self.subTest(schema=schema.__name__, values=values), self.assertRaises(ValidationError):
                    schema(**values)


if __name__ == "__main__":
    unittest.main()
