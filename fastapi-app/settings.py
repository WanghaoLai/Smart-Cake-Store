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
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Shanghai")
CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://smart-cake-store.vercel.app",
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
    # 所有数据库 datetime 统一采用 UTC；APP_TIMEZONE 仅用于展示边界。
    "timezone": "UTC"
}

# ---- 智能问答 / LLM ----
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# /chat/send 限流：每用户每窗口期最多 N 条（每条 = 一次 LLM + Embedding 成本）
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "20"))
CHAT_RATE_WINDOW_SECONDS = int(os.getenv("CHAT_RATE_WINDOW_SECONDS", "60"))

# 认证入口保护：账号维度防爆破，IP 维度防止攻击者轮换用户名。
AUTH_RATE_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_WINDOW_SECONDS", "300"))
LOGIN_RATE_LIMIT_PER_ACCOUNT = int(os.getenv("LOGIN_RATE_LIMIT_PER_ACCOUNT", "5"))
LOGIN_RATE_LIMIT_PER_IP = int(os.getenv("LOGIN_RATE_LIMIT_PER_IP", "30"))
REGISTER_RATE_LIMIT_PER_IP = int(os.getenv("REGISTER_RATE_LIMIT_PER_IP", "10"))

# 评价图片是普通用户可写磁盘的唯一入口：单文件限制外再加频率和总额。
REVIEW_UPLOAD_RATE_LIMIT = int(os.getenv("REVIEW_UPLOAD_RATE_LIMIT", "20"))
REVIEW_UPLOAD_RATE_WINDOW_SECONDS = int(os.getenv("REVIEW_UPLOAD_RATE_WINDOW_SECONDS", "3600"))
REVIEW_UPLOAD_USER_QUOTA_BYTES = int(os.getenv("REVIEW_UPLOAD_USER_QUOTA_BYTES", str(100 * 1024 * 1024)))
REVIEW_UPLOAD_GLOBAL_QUOTA_BYTES = int(os.getenv("REVIEW_UPLOAD_GLOBAL_QUOTA_BYTES", str(1024 * 1024 * 1024)))

# ---- 语义搜索 / 个性化推荐（纯规则，无 LLM）----
# heat_weight：热度对向量相似分的加成幅度（0 = 纯语义排序），可线上调参
SEMANTIC_SEARCH_CONFIG = {
    "candidate_k": int(os.getenv("SEARCH_CANDIDATE_K", "20")),
    "default_top_k": int(os.getenv("SEARCH_TOP_K", "10")),
    "heat_weight": float(os.getenv("SEARCH_HEAT_WEIGHT", "0.15")),
}
# 信号权重：收藏分类 > 购买分类 > 平均评分 > 销量热度
RECOMMEND_WEIGHTS = {
    "favorite_category": float(os.getenv("RECOMMEND_W_FAVORITE", "3.0")),
    "purchase_category": float(os.getenv("RECOMMEND_W_PURCHASE", "2.0")),
    "rating": float(os.getenv("RECOMMEND_W_RATING", "1.0")),
    "sales": float(os.getenv("RECOMMEND_W_SALES", "0.5")),
}

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
