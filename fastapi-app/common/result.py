from decimal import Decimal
from typing import Any, List

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from tortoise import Model


def _normalize(value: Any) -> Any:
    """递归把 Decimal 转成 float、ORM/Pydantic 模型转成 dict。

    金额自 DECIMAL 化之后，出参里混入了 Decimal。FastAPI 对 BaseModel 走
    model_dump(mode="json")，Decimal 会被序列化成字符串 "98.00"，而 dict 路径
    却是 float——两种形态前端都要兼容。统一在 Result.success 这个唯一出口
    归一化：保持历史的 JSON 数字形态，前端与既有 API 契约零变化。
    （精度问题的根源在存储与聚合，出参 float64 展示 2 位小数无损。）"""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python"))
    if isinstance(value, Model):
        return _normalize(dict(value))
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


class Result(BaseModel):
    code: str
    msg: str
    data: Any = None

    @staticmethod
    def success(data: Any = None):
        json_data = None
        if data is not None:
            json_data = jsonable_encoder(_normalize(data))
        return Result(code="200", msg="请求成功", data=json_data)

    @staticmethod
    def error(msg: str = "请求失败"):
        return Result(code="500", msg=msg)


class PageInfo(BaseModel):
    total: int = 0
    list: List[Any] = []
