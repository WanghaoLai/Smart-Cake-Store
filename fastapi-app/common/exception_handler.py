import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.responses import JSONResponse

logger = logging.getLogger("exception_handler")


# 自定义异常类
class CustomException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code


class ForbiddenException(CustomException):
    def __init__(self, message: str = "无权执行该操作"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundException(CustomException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictException(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_409_CONFLICT)


def _summarize_validation_error(exc: RequestValidationError) -> str:
    """提取首个字段级错误（位置 + 原因），让前端能直接看到是哪个字段错了。

    响应体保持统一格式，HTTP 状态使用标准 422；完整错误列表走服务端日志。"""
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
        msg = err.get("msg", "格式错误")
        if loc:
            return f"请求参数错误: {loc} - {msg}"
        return f"请求参数错误: {msg}"
    return "请求参数错误"


def setup_exceptions(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": str(exc.status_code), "msg": exc.detail}
        )

    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": str(exc.status_code), "msg": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def validate_exception_handler(request: Request, exc: RequestValidationError):
        # 完整错误列表进日志（含堆栈可定位），msg 只回首个错误避免响应过长
        logger.warning("422 %s %s errors=%s", request.method, request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content={"code": "422", "msg": _summarize_validation_error(exc)}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # 未知异常必须带堆栈落日志：print 到 stdout 会随部署环境丢失，且无级别/时间戳
        logger.exception("系统错误 %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "500", "msg": "系统错误"}
        )
