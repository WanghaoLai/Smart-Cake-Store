from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.responses import JSONResponse


# 自定义异常类
class CustomException(Exception):
    def __init__(self, message: str):
        self.message = message


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
            status_code=status.HTTP_200_OK,  # http总是返回200
            content={"code": "500", "msg": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def validate_exception_handler(request: Request, exc: RequestValidationError):
        print("捕获到422错误:", exc.errors())
        """处理422异常"""
        # 返回统一格式
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # http总是返回200
            content={"code": "500", "msg": "请求参数错误"}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        print("捕获到系统错误:", repr(exc))
        """处理所有异常"""
        # CORS 响应头统一由 CORSMiddleware 处理。
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # http总是返回200
            content={"code": "500", "msg": "系统错误"}
        )
