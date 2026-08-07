from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from api import api_router
from common.exception_handler import setup_exceptions

from common.result import Result
from settings import CORS_ORIGIN_REGEX, CORS_ORIGINS, TORTOISE_ORM

app = FastAPI()

# 前后端分离部署：生产环境使用显式来源白名单，避免任意站点调用业务 API。
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
    uvicorn.run("main:app", reload=True, port=9090, reload_dirs=["api", "agents", "common"])

