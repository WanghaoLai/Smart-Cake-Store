import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 fastapi-app/.env（已被 .gitignore 排除）
load_dotenv(Path(__file__).parent / ".env")


def _csv_env(name: str, default: str) -> list[str]:
    """Parse a comma-separated environment variable and discard empty values."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# ---- 运行环境 / 前后端跨域 ----
APP_ENV = os.getenv("APP_ENV", "development").lower()
CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
# 开发服务器可能自动选择其他端口；生产环境只接受 CORS_ORIGINS 白名单。
CORS_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1):\d+$"
    if APP_ENV == "development"
    else None
)

# ---- 数据库 ----
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "cake_store")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": DB_HOST,
                "port": DB_PORT,
                "database": DB_NAME,
                "user": DB_USER,
                "password": DB_PASSWORD,
                "minsize": 1,
                "maxsize": 10,
                "charset": "utf8mb4",
                "echo": False
            }
        },
    },
    "apps": {
      "models": {
          "models": ["models"],
          "default_connection": "default",
      }
    },
    "use_tz": True,
    "timezone": "Asia/Shanghai"
}

# ---- 智能问答 / LLM ----
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

AI_CONFIG = {
    "dashscope_api_key": DASHSCOPE_API_KEY,
    "model": os.getenv("LLM_MODEL", "qwen-turbo"),
    "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-v2"),
    "max_history": int(os.getenv("LLM_MAX_HISTORY", "20")),
    "top_k": int(os.getenv("RAG_TOP_K", "3")),
}

# ---- JWT ----
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# JWT 密钥强度校验：模块加载时即触发，问题暴露在启动阶段而非首次签发时
# 解决"密钥默认空串 → 任意人可伪造 token"的安全风险
# 阈值依据：NIST SP 800-107 推荐 HS256 对称密钥 ≥128 位（=16 字节），
# 生产环境保守起见要求 ≥32 字节（256 位）
_MIN_JWT_LEN_DEV = 16
_MIN_JWT_LEN_PROD = 32


def _validate_jwt_secret() -> None:
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY 未配置：请在 .env 中设置。"
            "生成命令：python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    length = len(JWT_SECRET_KEY)
    if APP_ENV != "development" and length < _MIN_JWT_LEN_PROD:
        raise RuntimeError(
            f"生产环境 JWT_SECRET_KEY 至少需要 {_MIN_JWT_LEN_PROD} 字符（当前 {length}）。"
            f"APP_ENV={APP_ENV!r}，请生成强随机密钥后重启。"
        )
    if length < _MIN_JWT_LEN_DEV:
        raise RuntimeError(
            f"JWT_SECRET_KEY 过短（{length} 字符），至少需要 {_MIN_JWT_LEN_DEV} 字符。"
        )
    if length < _MIN_JWT_LEN_PROD:
        # 开发环境仅告警不阻断，避免破坏现有 dev 流程
        import sys
        print(
            f"[settings] WARNING: JWT_SECRET_KEY 长度仅 {length} 字符，"
            f"建议升级到 ≥{_MIN_JWT_LEN_PROD} 字符以保证安全性",
            file=sys.stderr,
        )


_validate_jwt_secret()
