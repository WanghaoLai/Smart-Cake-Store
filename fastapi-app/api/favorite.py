from fastapi import APIRouter, Depends
from pydantic import BaseModel

from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result
from models import Favorite, Goods

router = APIRouter(prefix="/favorite", dependencies=[Depends(get_current_user)])


class FavoriteCreate(BaseModel):
    goods_id: int


@router.post("/add")
async def add(data: FavoriteCreate, current_user: dict = Depends(get_current_user)):
    existing = await Favorite.get_or_none(user_id=current_user["user_id"], goods_id=data.goods_id)
    if existing:
        raise CustomException("已经收藏过了")
    await Favorite.create(user_id=current_user["user_id"], goods_id=data.goods_id)
    return Result.success()


@router.delete("/remove/{goods_id}")
async def remove(goods_id: int, current_user: dict = Depends(get_current_user)):
    await Favorite.filter(user_id=current_user["user_id"], goods_id=goods_id).delete()
    return Result.success()


@router.get("/list")
async def fav_list(current_user: dict = Depends(get_current_user)):
    favorites = await Favorite.filter(user_id=current_user["user_id"]).prefetch_related("goods__category").order_by("-created_at")
    goods_list = []
    for fav in favorites:
        if fav.goods:
            g = fav.goods
            goods_list.append({
                "id": g.id,
                "name": g.name,
                "price": g.price,
                "description": g.description,
                "img": g.img,
                "num": g.num,
                "unit": g.unit,
                "categoryName": g.category.name if g.category else None,
                "categoryId": g.category.id if g.category else None,
            })
    return Result.success(goods_list)


@router.get("/check/{goods_id}")
async def check_fav(goods_id: int, current_user: dict = Depends(get_current_user)):
    fav = await Favorite.get_or_none(user_id=current_user["user_id"], goods_id=goods_id)
    return Result.success({"favorited": fav is not None})
