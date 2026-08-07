"""行政区级联只读接口：省 / 市 / 区县。

数据源是预置的 tb_province / tb_city / tb_town 三张表（地区代码静态，
不做增删改）。返回字段精简，避免每条记录带 ORM 元数据。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from common.auth import get_current_user
from common.exception_handler import CustomException
from common.result import Result
from models import City, Province, Town

router = APIRouter(prefix="/region", dependencies=[Depends(get_current_user)])


def _row(model, label_keys: dict[str, str]) -> dict:
    """Flatten ORM instance to a small dict. label_keys maps ORM attr → API key."""
    out = {"id": model.id}
    for attr, key in label_keys.items():
        out[key] = getattr(model, attr, None)
    return out


@router.get("/provinces")
async def list_provinces():
    """所有省份（含直辖市/自治区），按 id 升序。"""
    items = await Province.all().order_by("id")
    return Result.success([_row(p, {"name": "name", "area": "area"}) for p in items])


@router.get("/cities")
async def list_cities(provinceId: Optional[int] = Query(default=None, ge=1)):
    """指定省份下的城市；不传 provinceId 时返回全部城市（前端首次进入可惰性加载）。"""
    if provinceId is None:
        raise CustomException("请提供 provinceId 参数")
    items = await City.filter(province_id=provinceId).order_by("id")
    return Result.success([
        {**_row(c, {"name": "name"}), "provinceId": provinceId}
        for c in items
    ])


@router.get("/towns")
async def list_towns(cityId: Optional[int] = Query(default=None, ge=1)):
    """指定城市下的区县。"""
    if cityId is None:
        raise CustomException("请提供 cityId 参数")
    items = await Town.filter(city_id=cityId).order_by("id")
    return Result.success([
        {**_row(t, {"name": "name"}), "cityId": cityId}
        for t in items
    ])
