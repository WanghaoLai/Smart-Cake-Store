import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from common.auth import get_current_user
from main import app


class CreateConversationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": 7,
            "username": "tester",
            "role": "用户",
        }
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_current_user, None)

    def test_create_conversation_accepts_empty_body_for_first_visit(self):
        with patch(
            "api.chat.Conversation.create",
            new=AsyncMock(return_value=SimpleNamespace(id=11, title="新对话")),
        ) as create:
            response = self.client.post("/chat/conversation")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "200")
        self.assertEqual(response.json()["data"], {"id": 11, "title": "新对话"})
        create.assert_awaited_once_with(user_id=7, owner_role="用户", title="新对话")

    def test_create_conversation_ignores_legacy_json_payload(self):
        with patch(
            "api.chat.Conversation.create",
            new=AsyncMock(return_value=SimpleNamespace(id=12, title="新对话")),
        ) as create:
            response = self.client.post(
                "/chat/conversation",
                json={"title": "售后咨询"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"id": 12, "title": "新对话"})
        create.assert_awaited_once_with(user_id=7, owner_role="用户", title="新对话")


if __name__ == "__main__":
    unittest.main()
