from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import settings


DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    query={
        "charset": "utf8mb4"
    }
)


engine = create_engine(
    DATABASE_URL,

    # 每次从连接池取连接之前先检查连接是否还有效
    pool_pre_ping=True,

    # 定期重新建立连接，避免云 MySQL 主动断开长时间连接
    pool_recycle=1800,

    # 基础连接池大小
    pool_size=5,

    # 临时允许额外连接
    max_overflow=10,

    # 获取连接最大等待时间
    pool_timeout=30,

    echo=False
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():
    """
    FastAPI 数据库依赖。
    """
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()