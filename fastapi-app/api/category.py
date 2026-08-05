from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import create_model
from tortoise.contrib.pydantic import pydantic_model_creator

from common.auth import get_current_user, get_current_admin
from common.result import Result, PageInfo
from models import Category

router = APIRouter(prefix="/category")

# 创建 pydantic 只读模型 把数据库模型转化成pydantic模型
CategoryPydantic = pydantic_model_creator(Category)
# 自动生成所有字段为 Optional 的更新模型
CategoryCreatePydantic = create_model(
    "CategoryPydantic",
    **{
        # 从只读模型中读取所有字段然后给它设置成可选
        name: (Optional[field.annotation], None)
        for name, field in CategoryPydantic.model_fields.items()
    }
)


@router.post("/add", dependencies=[Depends(get_current_admin)])
async def add(category_pydantic: CategoryCreatePydantic):
    create_data = category_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await Category.create(**create_data)
    return Result.success()


@router.put("/update", dependencies=[Depends(get_current_admin)])
async def update(category_pydantic: CategoryCreatePydantic):
    update_data = category_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await Category.filter(id=category_pydantic.id).update(**update_data)
    return Result.success()


@router.delete("/delete/{user_id}", dependencies=[Depends(get_current_admin)])
async def delete(user_id: int):
    await Category.filter(id=user_id).delete()
    return Result.success()


@router.get("/selectPage", dependencies=[Depends(get_current_user)])
async def select(name: str = "", pageNum: int = 1, pageSize: int = 5):
    # 同时获取分页数据和总数
    query = Category.filter(name__contains=name)
    # 获取分页数据
    category_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    category_list = [
        # 遍历每个 Category 实例（ORM实例），通过 Pydantic 模型，转为字典
        CategoryPydantic.model_validate(category).model_dump()
        for category in category_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=category_list)
    return Result.success(pageinfo)


# 查询所有
@router.get("/selectAll", dependencies=[Depends(get_current_user)])
async def select_all(name: str = ""):
    category_list = await Category.filter(name__contains=name) # 模糊查询
    return Result.success(category_list)


