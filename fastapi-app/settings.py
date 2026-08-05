import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 fastapi-app/.env（已被 .gitignore 排除）
load_dotenv(Path(__file__).parent / ".env")

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
