import os
from dotenv import load_dotenv


# 本地运行时读取 .env
# Render 环境中如果没有 .env，也不会报错，
# 会直接读取 Render Dashboard 中配置的环境变量
load_dotenv()


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")

    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")


settings = Settings()