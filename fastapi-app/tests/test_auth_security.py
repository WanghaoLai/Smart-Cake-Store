"""认证安全不变量：强制改密由后端执行，改密后旧 Token 立即失效。"""
import unittest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from tortoise import Tortoise

from common.auth import create_access_token, get_current_user, validate_password
from common.exception_handler import CustomException
from models import User


def _request(path: str) -> Request:
    return Request({"type": "http", "method": "GET", "path": path, "headers": []})


class AuthSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        self.user = await User.create(
            id=1,
            username="security-user",
            password="hash",
            role="用户",
            must_change_password=True,
            token_version=3,
        )
        token = create_access_token({
            "id": self.user.id,
            "username": self.user.username,
            "role": "用户",
            "token_version": self.user.token_version,
        })
        self.credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_forced_password_change_blocks_every_other_authenticated_route(self):
        with self.assertRaises(HTTPException) as ctx:
            await get_current_user(_request("/orders/selectPage"), self.credentials)
        self.assertEqual(ctx.exception.status_code, 403)
        payload = await get_current_user(_request("/updatePassword"), self.credentials)
        self.assertEqual(payload["user_id"], self.user.id)

    async def test_token_version_revokes_existing_token(self):
        await User.filter(id=self.user.id).update(token_version=4, must_change_password=False)
        with self.assertRaises(HTTPException) as ctx:
            await get_current_user(_request("/stats/home"), self.credentials)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_server_side_password_policy_rejects_short_and_common_passwords(self):
        for password in ("short", "password", "12345678"):
            with self.subTest(password=password), self.assertRaises(CustomException):
                validate_password(password)
        validate_password("correct-horse-battery-staple")


if __name__ == "__main__":
    unittest.main()
