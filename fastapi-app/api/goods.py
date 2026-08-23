import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction

from common.auth import get_current_user, get_current_admin
from common.exception_handler import CustomException
from common.pagination import clamp_page
from common.result import Result, PageInfo
from models import Favorite, Goods, IndexTask, Orders, Review
from agents.rag import index_task_service
from agents.recommendation import search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goods", dependencies=[Depends(get_current_user)])

GoodsPydantic = pydantic_model_creator(Goods)


class _GoodsWriteBase(BaseModel):
    """商品可写字段白名单；关系对象、反向关系和服务端字段不能由请求注入。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: Optional[str] = Field(None, max_length=255)
    detail: Optional[str] = None
    ingredients: Optional[str] = Field(None, max_length=500)
    specs: Optional[str] = Field(None, max_length=255)
    shelf_life: Optional[str] = Field(None, max_length=100, alias="shelfLife")
    weight: Optional[str] = Field(None, max_length=100)
    origin: Optional[str] = Field(None, max_length=100)
    serves: Optional[str] = Field(None, max_length=100)
    img: Optional[str] = Field(None, max_length=255)
    unit: Optional[str] = Field(None, max_length=255)
    category_id: Optional[int] = Field(None, gt=0, alias="categoryId")

    @field_validator("description", "detail", "ingredients", "specs", "shelf_life",
                     "weight", "origin", "serves", "img", "unit", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class GoodsCreate(_GoodsWriteBase):
    name: str = Field(..., min_length=1, max_length=255)
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    num: int = Field(..., ge=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("商品名称不能为空")
        return value


class GoodsUpdate(_GoodsWriteBase):
    id: int = Field(..., gt=0)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    num: Optional[int] = Field(None, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_update_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("商品名称不能为空")
        return value

    @model_validator(mode="after")
    def require_change(self):
        if not (self.model_fields_set - {"id"}):
            raise ValueError("至少需要提供一个待更新字段")
        return self


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
async def add(goods_pydantic: GoodsCreate, background_tasks: BackgroundTasks):
    create_data = goods_pydantic.model_dump(exclude_unset=True)
    async with in_transaction():
        goods = await Goods.create(**create_data)
        task = await IndexTask.create(
            entity_type='goods', entity_id=goods.id, action='upsert',
        )
    background_tasks.add_task(_process_index_task_safe, task.id)
    return Result.success()


@router.put("/update", dependencies=[Depends(get_current_admin)])
async def update(goods_pydantic: GoodsUpdate, background_tasks: BackgroundTasks):
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
        if await Orders.filter(goods_id=goods_id).exists() or await Review.filter(goods_id=goods_id).exists():
            raise CustomException("商品已产生订单或评价，为保留审计记录不能删除")
        # 收藏是可派生关系；无交易记录时可随商品一并清理。
        await Favorite.filter(goods_id=goods_id).delete()
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


@router.get("/search")
async def semantic_search(q: str = "", top_k: int = 10):
    """语义搜索：自然语言描述直达商品（复用客服商品向量索引）。
    三级兜底（向量 → 关键字 → 热销），mode 字段告知前端命中哪一级。"""
    top_k = min(max(top_k, 1), 50)
    data = await search(q, top_k)
    return Result.success(data)


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
