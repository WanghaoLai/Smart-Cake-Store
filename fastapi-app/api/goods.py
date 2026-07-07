from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator

from common.auth import get_current_user
from common.result import Result, PageInfo
from models import Goods
from services.knowledge_service import knowledge_service

router = APIRouter(prefix="/goods", dependencies=[Depends(get_current_user)])

GoodsPydantic = pydantic_model_creator(Goods)
GoodsCreatePydantic = create_model(
    "GoodsPydantic",
    **{
        name: (Optional[field.annotation], None)
        for name, field in GoodsPydantic.model_fields.items()
    },
    category_id=(Optional[int], Field(None, alias="categoryId"))
)


@router.post("/add")
async def add(goods_pydantic: GoodsCreatePydantic):
    create_data = goods_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    goods = await Goods.create(**create_data)
    await goods.fetch_related('category')
    knowledge_service.sync_goods(goods)
    return Result.success()


@router.put("/update")
async def update(goods_pydantic: GoodsCreatePydantic):
    update_data = goods_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await Goods.filter(id=goods_pydantic.id).update(**update_data)
    goods = await Goods.get(id=goods_pydantic.id).prefetch_related('category')
    knowledge_service.sync_goods(goods)
    return Result.success()


@router.delete("/delete/{goods_id}")
async def delete(goods_id: int):
    await Goods.filter(id=goods_id).delete()
    knowledge_service.remove_goods(goods_id)
    return Result.success()

@router.get("/selectPage")
async def select(name: str = "", categoryId: int = 0, pageNum: int = 1, pageSize: int = 5):
    # 同时获取分页数据和总数
    query = Goods.filter(name__contains=name).prefetch_related('category') # 进行表关联
    if categoryId > 0:
        query = query.filter(category_id=categoryId)
    # 获取分页数据
    goods_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    goods_list = [
        {
            **GoodsPydantic.model_validate(goods).model_dump(),  # id=xxx,no=xxx,name=xxx
            "categoryName": goods.category.name if goods.category else None,
            "categoryId": goods.category.id if goods.category else None,
        }
        for goods in goods_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=goods_list)
    return Result.success(pageinfo)