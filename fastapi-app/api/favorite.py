from fastapi import APIRouter, Depends
from pydantic import BaseModel
from tortoise.exceptions import IntegrityError

from common.auth import get_current_customer
from common.exception_handler import CustomException
from common.pagination import clamp_page
from common.result import PageInfo, Result
from models import Favorite, Goods

router = APIRouter(prefix="/favorite", dependencies=[Depends(get_current_customer)])


class FavoriteCreate(BaseModel):
    goods_id: int


@router.post("/add")
async def add(data: FavoriteCreate, current_user: dict = Depends(get_current_customer)):
    if not await Goods.filter(id=data.goods_id).exists():
        raise CustomException("商品不存在")
    existing = await Favorite.get_or_none(user_id=current_user["user_id"], goods_id=data.goods_id)
    if existing:
        return Result.success()
    try:
        await Favorite.create(user_id=current_user["user_id"], goods_id=data.goods_id)
    except IntegrityError:
        # 两个并发收藏请求由唯一约束收敛为同一个成功结果。
        if not await Favorite.filter(user_id=current_user["user_id"], goods_id=data.goods_id).exists():
            raise
    return Result.success()


@router.delete("/remove/{goods_id}")
async def remove(goods_id: int, current_user: dict = Depends(get_current_customer)):
    await Favorite.filter(user_id=current_user["user_id"], goods_id=goods_id).delete()
    return Result.success()


@router.get("/list")
async def fav_list(pageNum: int = 1, pageSize: int = 20, current_user: dict = Depends(get_current_customer)):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = Favorite.filter(user_id=current_user["user_id"])
    total = await query.count()
    favorites = await query.prefetch_related("goods__category").order_by("-created_at").offset((pageNum - 1) * pageSize).limit(pageSize)
    goods_list = []
    for fav in favorites:
        if fav.goods:
            g = fav.goods
            goods_list.append({
                "id": g.id,
                "name": g.name,
                "specs": g.specs,
                "price": g.price,
                "description": g.description,
                "img": g.img,
                "num": g.num,
                "unit": g.unit,
                "categoryName": g.category.name if g.category else None,
                "categoryId": g.category.id if g.category else None,
            })
    return Result.success(PageInfo(total=total, list=goods_list))


@router.get("/check/{goods_id}")
async def check_fav(goods_id: int, current_user: dict = Depends(get_current_customer)):
    fav = await Favorite.get_or_none(user_id=current_user["user_id"], goods_id=goods_id)
    return Result.success({"favorited": fav is not None})
