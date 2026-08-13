from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from core.database import get_db
from core.config import settings


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
        "environment": settings.APP_ENV
    }


@router.get("/db")
def database_health(db: Session = Depends(get_db)):
    """
    测试 FastAPI -> MySQL 数据库连接。
    """

    try:
        result = db.execute(
            text("SELECT 1 AS connection_test")
        )

        row = result.fetchone()

        return {
            "status": "ok",
            "database": "connected",
            "connection_test": row.connection_test
        }

    except SQLAlchemyError as e:

        return {
            "status": "error",
            "database": "connection_failed",
            "error_type": type(e).__name__,
            "message": str(e)
        }


@router.get("/db/info")
def database_info(db: Session = Depends(get_db)):
    """
    获取数据库基本信息。
    用于确认实际连接的是哪台数据库。
    """

    try:
        result = db.execute(
            text(
                """
                SELECT
                    DATABASE() AS database_name,
                    VERSION() AS mysql_version,
                    CURRENT_USER() AS current_user,
                    @@hostname AS mysql_hostname
                """
            )
        )

        row = result.fetchone()

        return {
            "status": "ok",
            "database": {
                "database_name": row.database_name,
                "mysql_version": row.mysql_version,
                "current_user": row.current_user,
                "mysql_hostname": row.mysql_hostname
            }
        }

    except SQLAlchemyError as e:

        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }