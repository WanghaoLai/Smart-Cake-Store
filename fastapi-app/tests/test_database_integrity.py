"""数据库是并发业务不变量的最终防线。"""
import unittest
from pathlib import Path

from tortoise import Tortoise
from tortoise.exceptions import IntegrityError

from models import Favorite, Goods, User


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


class DatabaseModelIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_username_and_favorite_are_unique_under_concurrency_boundary(self):
        user = await User.create(username="unique-user", password="hash", role="用户")
        with self.assertRaises(IntegrityError):
            await User.create(username="unique-user", password="other", role="用户")
        goods = await Goods.create(name="cake", price=10, num=1)
        await Favorite.create(user_id=user.id, goods_id=goods.id)
        with self.assertRaises(IntegrityError):
            await Favorite.create(user_id=user.id, goods_id=goods.id)


class MigrationIntegrityTests(unittest.TestCase):
    def test_security_migration_is_part_of_baseline_and_never_hardcodes_database(self):
        baseline = (PROJECT_DIR / "db" / "cake_store.sql").read_text(encoding="utf-8")
        migration = (PROJECT_DIR / "db" / "migrations" / "010_security_integrity.sql").read_text(encoding="utf-8")
        recommendations = (PROJECT_DIR / "db" / "migrations" / "011_review_recommendations.sql").read_text(encoding="utf-8")
        self.assertIn("010_security_integrity.sql", baseline)
        self.assertNotIn("USE `cake_store`", migration)
        self.assertIn("011_review_recommendations.sql", baseline)
        self.assertNotIn("USE `cake_store`", recommendations)
        for required in ("NOT NULL", "claim_token", "processing_started_at", "INTERVAL 8 HOUR"):
            self.assertIn(required, recommendations)
        for required in (
            "token_version", "uk_user_username", "uk_favorite_user_goods",
            "uk_address_one_default", "fk_orders_user", "ck_review_rating",
            "idx_orders_status_time",
        ):
            self.assertIn(required, migration)


if __name__ == "__main__":
    unittest.main()
