import asyncio
from tortoise import Tortoise
from models import Goods
from settings import TORTOISE_ORM


async def direct_query(query: str) -> str:
    """数据库查询"""
    await Tortoise.init(config=TORTOISE_ORM)
    goods = await Goods.filter(name__contains=query).first()
    if goods:
        return f"商品信息：{goods.name}，价格：{goods.price}元，描述：{goods.description}"
    return "商品信息查询失败！"

if __name__ == "__main__":
    goods_name = input("请输入商品名称：")
    result = asyncio.run(direct_query(query=goods_name))
    # result = direct_query(goods_name)
    print(result)


