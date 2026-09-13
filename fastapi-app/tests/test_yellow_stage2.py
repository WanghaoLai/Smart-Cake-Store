"""第二阶段：地址、收藏、评价和资金请求的一致性。"""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from tortoise import Tortoise

from api.address import AddressCreatePydantic, add as add_address
from api.favorite import FavoriteCreate, add as add_favorite, fav_list
from api.files import _delete_unreferenced_review
from api.reviews import ReviewReplyPydantic, list_by_goods
from common.exception_handler import CustomException
from models import City, Favorite, Goods, Province, Review, Town, User


class UserDataIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["models"]})
        await Tortoise.generate_schemas()
        self.user = await User.create(id=1, username="buyer", role="用户")
        self.other = await User.create(id=2, username="other", role="用户")
        self.goods = await Goods.create(id=1, name="蛋糕", price=20, num=5)
        self.province = await Province.create(id=1, name="甲省")
        self.other_province = await Province.create(id=2, name="乙省")
        self.city = await City.create(id=11, name="甲市", province_id=1)
        self.town = await Town.create(id=111, name="甲区", city_id=11)
        self.current = {"user_id": 1, "username": "buyer", "role": "用户"}

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_address_requires_deliverable_fields_and_region_chain(self):
        with self.assertRaises(CustomException):
            await add_address(AddressCreatePydantic(), self.current)
        with self.assertRaises(CustomException):
            await add_address(AddressCreatePydantic(
                name="张三", phone="13800138000", detail="1号",
                provinceId=2, cityId=11, townId=111,
            ), self.current)
        result = await add_address(AddressCreatePydantic(
            name=" 张三 ", phone="13800138000", detail=" 1号 ",
            provinceId=1, cityId=11, townId=111,
        ), self.current)
        self.assertEqual(result.code, "200")

    async def test_favorite_add_is_idempotent_and_list_is_paginated(self):
        await add_favorite(FavoriteCreate(goods_id=1), self.current)
        await add_favorite(FavoriteCreate(goods_id=1), self.current)
        self.assertEqual(await Favorite.all().count(), 1)
        result = await fav_list(1, 20, self.current)
        self.assertEqual(result.data["total"], 1)
        self.assertEqual(result.data["list"][0]["id"], 1)
        with self.assertRaises(CustomException):
            await add_favorite(FavoriteCreate(goods_id=999), self.current)

    async def test_review_summary_uses_all_rows_not_loaded_page(self):
        await Review.create(goods_id=1, user_id=1, rating=1, time=datetime.now(timezone.utc))
        await Review.create(goods_id=1, user_id=2, rating=5, time=datetime.now(timezone.utc))
        result = await list_by_goods(1, 1, 1)
        self.assertEqual(result.data["total"], 2)
        self.assertEqual(result.data["averageRating"], 3.0)
        self.assertEqual(len(result.data["list"]), 1)

    def test_review_reply_has_bounded_length(self):
        with self.assertRaises(ValidationError):
            ReviewReplyPydantic(reply="x" * 1001)

    async def test_only_owner_can_delete_unreferenced_review_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            review_dir = Path(directory) / "review"
            review_dir.mkdir()
            filename = "user_1_" + "a" * 32 + ".png"
            (review_dir / filename).write_bytes(b"png")
            path = f"files/download/review/{filename}"
            with patch("api.files.UPLOAD_DIR", Path(directory)):
                with self.assertRaises(CustomException):
                    await _delete_unreferenced_review(path, 2)
                self.assertTrue(await _delete_unreferenced_review(path, 1))
                self.assertFalse((review_dir / filename).exists())


if __name__ == "__main__":
    unittest.main()
