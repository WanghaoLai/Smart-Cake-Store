"""健康检查不得向公网暴露数据库基础设施细节。"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app


class HealthSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_public_db_probe_returns_only_generic_failure(self):
        with patch("api.health._probe", new=AsyncMock(return_value={"status": "error"})):
            response = self.client.get("/health/db")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "error", "database": "connection_failed"})
        self.assertNotIn("message", response.json())

    def test_database_info_requires_admin_authentication(self):
        response = self.client.get("/health/db/info")
        self.assertIn(response.status_code, {401, 403})


if __name__ == "__main__":
    unittest.main()
