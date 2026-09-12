"""Create an initial administrator explicitly; never reset an existing account.
Run: python3 scripts/bootstrap_admin.py --username YOUR_ADMIN
Password is prompted without echo; no built-in or logged credentials.
"""
import argparse
import asyncio
from getpass import getpass
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tortoise import Tortoise
from common.auth import hash_password, validate_password
from models import Admin
from settings import TORTOISE_ORM

async def create_initial_admin(username, password):
    validate_password(password)
    if not username.strip() or len(username) > 64:
        raise ValueError("管理员账号长度必须为 1 到 64")
    if await Admin.filter(username=username).exists():
        raise ValueError("账号已存在，初始化不会覆盖已有管理员")
    await Admin.create(username=username, password=hash_password(password), name=username,
                       role="管理员", must_change_password=False)

async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = getpass("设置管理员密码：")
    if password != getpass("再次输入密码："):
        raise ValueError("两次密码不一致")
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        await create_initial_admin(args.username, password)
        print("管理员已创建。")
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
