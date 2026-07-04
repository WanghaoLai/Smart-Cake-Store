TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": "localhost",
                "port": 3306,
                "database": "cake_store",  # 数据库名称
                "user": "root",
                "password": "REDACTED_DB_PASSWORD",  # 数据库密码
                "minsize": 1,
                "maxsize": 10,
                "charset": "utf8mb4",
                "echo": True
            }
        },
    },
    "apps": {
      "models": {
          "models": ["models"],
          "default_connection": "default",
      }
    },
    "use_tz": True,  # 是否使用时区
    "timezone": "Asia/Shanghai"
}

# 智能问答配置
AI_CONFIG = {
    "dashscope_api_key": "REDACTED_DASHSCOPE_KEY",  # 通义千问 API Key，需要替换为实际的 key
    "model": "qwen-turbo",  # 模型选择: qwen-turbo, qwen-plus, qwen-max
    "embedding_model": "text-embedding-v2",  # Embedding 模型
    "max_history": 20,  # 最大历史消息数
    "top_k": 3,  # RAG 检索数量
}

# JWT 配置
JWT_SECRET_KEY = "REDACTED_JWT_SECRET"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

