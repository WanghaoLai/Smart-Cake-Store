from typing import List, Optional

from fastapi import APIRouter
from pydantic import create_model
from tortoise.contrib.pydantic import pydantic_model_creator

from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Admin

router = APIRouter(prefix="/admin")
# 创建 pydantic 只读模型 把数据库模型转化成pydantic模型
AdminPydantic = pydantic_model_creator(Admin)
# 自动生成所有字段为 Optional 的更新模型
AdminCreatePydantic = create_model(
    "AdminPydantic",
    **{
        # 从只读模型中读取所有字段然后给它设置成可选
        name: (Optional[field.annotation], None)
        for name, field in AdminPydantic.model_fields.items()
    }
)


# 新增
@router.post("/add")
async def add(admin_create_pydantic: AdminCreatePydantic):
    admin = await Admin.get_or_none(username=admin_create_pydantic.username)
    if admin is not None:
        raise CustomException("账号重复")
    if admin_create_pydantic.name is None:
        admin_create_pydantic.name = admin_create_pydantic.username
    if admin_create_pydantic.password is None:
        admin_create_pydantic.password = "admin"
    create_data = admin_create_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    create_data['role'] = '管理员'
    await Admin.create(**create_data)
    return Result.success()


# 修改
@router.put("/update")
async def update(admin_create_pydantic: AdminCreatePydantic):
    update_data = admin_create_pydantic.model_dump(exclude_unset=True, exclude={'id'})
    await Admin.filter(id=admin_create_pydantic.id).update(**update_data)
    return Result.success()


# 删除
@router.delete("/delete/{admin_id}")
async def delete(admin_id: int):
    await Admin.filter(id=admin_id).delete()
    return Result.success()


# 批量删除
@router.delete("/deleteBatch")
async def delete_batch(ids: List[int]):
    await Admin.filter(id__in=ids).delete()
    return Result.success()


# 单个查询
@router.get("/selectById/{admin_id}")
async def select_one(admin_id: int):
    admin = await Admin.get(id=admin_id)
    return Result.success(admin)


# 查询所有
@router.get("/selectAll")
async def select_all(name: str = ""):
    admin_list = await Admin.filter(name__contains=name) # 模糊查询
    return Result.success(admin_list)


# 分页查询
@router.get("/selectPage")
async def select_page(name: str = "", pageNum: int = 1, pageSize: int = 10):
    # 同时获取分页数据和总数
    query = Admin.filter(name__contains=name)
    # 获取分页数据
    admin_list = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    admin_list = [
        # 遍历每个 Admin 实例（ORM实例），通过 Pydantic 模型，转为字典
        AdminPydantic.model_validate(admin).model_dump()
        for admin in admin_list
    ]
    # 计算总数
    total = await query.count()
    # 封装分页数据
    pageinfo = PageInfo(total=total, list=admin_list)
    return Result.success(pageinfo)
