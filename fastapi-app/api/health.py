"""健康检查：探测进程存活与应用真实使用的 Tortoise 连接池。

历史版本用独立 SQLAlchemy 引擎探测 /health/db，测的不是业务链路，
且依赖 chromadb 的传递依赖才能 import——本版本已整体移除 core/ 双 ORM 栈。"""
from fastapi import APIRouter
from tortoise import Tortoise

from settings import APP_ENV

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("")
def health():
    """
    测试 FastAPI 服务是否正常。
    不访问数据库。
    """
    return {
        "status": "ok",
        "service": "fastapi",
        "environment": APP_ENV
    }


async def _probe(query: str) -> dict:
    """走应用注册的 default 连接执行探测 SQL，异常翻译成结构化错误。"""
    try:
        conn = Tortoise.get_connection("default")
        rows = await conn.execute_query_dict(query)
        return {"status": "ok", **rows[0]}
    except Exception as e:  # noqa: BLE001 - 健康检查要把任何失败转成结构化响应
        return {"status": "error", "error_type": type(e).__name__, "message": str(e)}


@router.get("/db")
async def database_health():
    """
    测试 FastAPI -> MySQL 数据库连接（与应用共用 Tortoise 连接池）。
    """
    result = await _probe("SELECT 1 AS connection_test")
    if result["status"] == "ok":
        result["database"] = "connected"
    else:
        result["database"] = "connection_failed"
    return result


@router.get("/db/info")
async def database_info():
    """
    获取数据库基本信息。
    用于确认实际连接的是哪台数据库。
    """
    return await _probe(
        "SELECT DATABASE() AS `database_name`, VERSION() AS `mysql_version`, "
        "CURRENT_USER() AS `current_user`, @@hostname AS `mysql_hostname`"
    )
