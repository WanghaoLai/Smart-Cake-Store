import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from tortoise import Tortoise
from api.user import router as user_router
from api.files import router as files_router
from api.auth_schemas import LoginRequest
from common.auth import get_current_admin, get_current_user, verify_password
from common.exception_handler import setup_exceptions
from models import User

class RepairHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:",modules={"models":["models"]})
        await Tortoise.generate_schemas()
        await User.create(id=7,username="buyer",password="old",token_version=2)
        self.app=FastAPI();setup_exceptions(self.app)
        self.app.include_router(user_router);self.app.include_router(files_router)
        self.app.dependency_overrides[get_current_user]=lambda:{"user_id":7,"role":"用户"}
        self.app.dependency_overrides[get_current_admin]=lambda:{"user_id":1,"role":"管理员"}
        @self.app.post('/test-login')
        def login(data:LoginRequest): return {}
        self.client=AsyncClient(transport=ASGITransport(app=self.app),base_url="http://test")
    async def asyncTearDown(self):
        await self.client.aclose();await Tortoise.close_connections()
    async def test_password_only_reset_contract_and_revocation(self):
        response=await self.client.put('/user/reset-password/7',json={"password":"Safe-Reset-2026"})
        self.assertEqual(response.status_code,200,response.text)
        user=await User.get(id=7)
        self.assertTrue(verify_password("Safe-Reset-2026",user.password))
        self.assertEqual(user.token_version,3)
        self.assertTrue(user.must_change_password)
    async def test_validation_log_does_not_contain_password_input(self):
        with self.assertLogs("exception_handler",level="WARNING") as logs:
            response=await self.client.post('/test-login',json={"password":"DO-NOT-LOG-THIS"})
        self.assertEqual(response.status_code,422)
        self.assertNotIn("DO-NOT-LOG-THIS",str(logs.output))
    async def test_customer_avatar_upload_is_scoped_and_goods_remains_admin_only(self):
        with tempfile.TemporaryDirectory() as tmp,patch('api.files.UPLOAD_DIR',Path(tmp)):
            response=await self.client.post('/files/upload_avatar',files={"file":("avatar.png",b'\x89PNG\r\n\x1a\nimage','image/png')})
            self.assertEqual(response.status_code,200,response.text)
            self.assertIn('avatar/user_7_',response.json()['data'])
            self.app.dependency_overrides.pop(get_current_admin)
            denied=await self.client.post('/files/upload?category=goods',files={"file":("x.png",b'\x89PNG\r\n\x1a\nimage','image/png')})
            self.assertEqual(denied.status_code,403,denied.text)
