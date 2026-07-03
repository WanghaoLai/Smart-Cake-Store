from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from api import api_router
from common.exception_handler import setup_exceptions

from common.result import Result
from settings import TORTOISE_ORM

app = FastAPI()

# 跨域配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 配置路由
app.include_router(api_router)
# 注册orm
register_tortoise(app, config=TORTOISE_ORM, add_exception_handlers=True)
# 注册异常处理器
setup_exceptions(app)

@app.get("/")
async def root():
    return Result.success()

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, port=9090)

