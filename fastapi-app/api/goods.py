import logging
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import create_model, Field
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction

from common.auth import get_current_user, get_current_admin
from common.pagination import clamp_page
from common.result import Result, PageInfo
from models import Goods, IndexTask
from agents.rag import index_task_service

logger = logging.getLogger(__name__)

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


async def _process_index_task_safe(task_id: int) -> None:
    """BackgroundTasks 入口：异常不许逃逸污染任务栈，
    但必须落日志——配置错误/代码 bug 这类非预期失败如果静默消失，
    run-pending 兜底机制本身坏了也无从发现。可重试的索引失败仍由
    IndexTask 表的 attempts/last_error 记录，/index/run-pending 兜底。"""
    try:
        await index_task_service.process(task_id)
    except Exception:
        logger.exception("index task %s 处理失败", task_id)


@router.post("/add", dependencies=[Depends(get_current_admin)])
async def add(goods_pydantic: GoodsCreatePydantic, background_tasks: BackgroundTasks):
    create_data = goods_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    async with in_transaction():
        goods = await Goods.create(**create_data)
        task = await IndexTask.create(
            entity_type='goods', entity_id=goods.id, action='upsert',
        )
    background_tasks.add_task(_process_index_task_safe, task.id)
    return Result.success()


@router.put("/update", dependencies=[Depends(get_current_admin)])
async def update(goods_pydantic: GoodsCreatePydantic, background_tasks: BackgroundTasks):
    update_data = goods_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    async with in_transaction():
        affected = await Goods.filter(id=goods_pydantic.id).update(**update_data)
        task = None
        if affected > 0:
            task = await IndexTask.create(
                entity_type='goods', entity_id=goods_pydantic.id, action='upsert',
            )
    if task is not None:
        background_tasks.add_task(_process_index_task_safe, task.id)
    return Result.success()


@router.delete("/delete/{goods_id}", dependencies=[Depends(get_current_admin)])
async def delete(goods_id: int, background_tasks: BackgroundTasks):
    async with in_transaction():
        affected = await Goods.filter(id=goods_id).delete()
        task = None
        if affected > 0:
            task = await IndexTask.create(
                entity_type='goods', entity_id=goods_id, action='delete',
            )
    if task is not None:
        background_tasks.add_task(_process_index_task_safe, task.id)
    return Result.success()


@router.get("/selectPage")
async def select(name: str = "", categoryId: int = 0, pageNum: int = 1, pageSize: int = 5):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
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


@router.get("/detail/{goods_id}")
async def detail(goods_id: int):
    """商品详情：返回完整字段（含 detail/ingredients/specs/shelf_life/weight/origin/serves）"""
    goods = await Goods.filter(id=goods_id).prefetch_related('category').first()
    if goods is None:
        return Result.error("商品不存在或已下架")
    return Result.success({
        **GoodsPydantic.model_validate(goods).model_dump(),
        "categoryName": goods.category.name if goods.category else None,
        "categoryId": goods.category.id if goods.category else None,
    })
