import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from tortoise import Tortoise
from settings import TORTOISE_ORM
from models import Goods


async def get_goods_by_name(name: str):
    """根据商品名称获取商品的所有信息"""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        goods = await Goods.filter(name=name).first()
        if goods:
            print(f"商品信息:")
            print(f"  ID: {goods.id}")
            print(f"  名称: {goods.name}")
            print(f"  价格: {goods.price}")
            print(f"  描述: {goods.description}")
            print(f"  图片: {goods.img}")
            print(f"  库存: {goods.num}")
            print(f"  单位: {goods.unit}")
            print(f"  分类ID: {goods.category_id}")
            return goods
        else:
            print(f"未找到名称为 '{name}' 的商品")
            return None
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    goods_name = input("请输入商品名称: ")
    asyncio.run(get_goods_by_name(goods_name))