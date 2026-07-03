import asyncio
from tortoise import Tortoise
from settings import TORTOISE_ORM
from models import Conversation, Message


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    print("数据库表创建成功！")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(init_db())
