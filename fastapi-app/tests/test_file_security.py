"""文件上传需要同时限制单文件、真实格式和累计配额。"""
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile

from api.files import _save
from common.exception_handler import CustomException


PNG = b"\x89PNG\r\n\x1a\n" + b"safe-test-payload"


class FileSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_extension_spoofing_and_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp, patch("api.files.UPLOAD_DIR", Path(tmp)):
            upload = UploadFile(filename="fake.png", file=BytesIO(b"not-an-image"))
            with self.assertRaises(CustomException):
                await _save(upload, "review", owner_id=7)
            review_dir = Path(tmp) / "review"
            self.assertEqual(list(review_dir.iterdir()), [])

    async def test_valid_image_is_attributed_and_user_quota_is_enforced(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("api.files.UPLOAD_DIR", Path(tmp)),
            patch("api.files.REVIEW_UPLOAD_USER_QUOTA_BYTES", len(PNG) + 1),
            patch("api.files.REVIEW_UPLOAD_GLOBAL_QUOTA_BYTES", 1024),
        ):
            first = UploadFile(filename="one.png", file=BytesIO(PNG))
            rel = await _save(first, "review", owner_id=7)
            self.assertTrue(Path(rel).name.startswith("user_7_"))

            second = UploadFile(filename="two.png", file=BytesIO(PNG))
            with self.assertRaises(CustomException):
                await _save(second, "review", owner_id=7)
            self.assertEqual(len(list((Path(tmp) / "review").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
