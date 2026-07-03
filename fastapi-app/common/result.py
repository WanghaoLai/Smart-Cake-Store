from typing import Any, List

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from tortoise import Model


class Result(BaseModel):
    code: str
    msg: str
    data: Any = None

    @staticmethod
    def success(data: Any = None):
        json_data = None
        if data is not None:
            json_data = jsonable_encoder(data)
        return Result(code="200", msg="请求成功", data=json_data)


    @staticmethod
    def error(msg: str = "请求失败"):
        return Result(code="500", msg=msg)


class PageInfo(BaseModel):
    total: int = 0
    list: List[Any] = []
