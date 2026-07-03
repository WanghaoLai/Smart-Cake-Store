import os

from dotenv import load_dotenv

load_dotenv("/Users/xiaohao/Python/Cake_store/free_system/fastapi-app/agent/.env")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

XIAOMI_MIMO_MODEL = os.getenv("XIAOMI_MIMO_MODEL")
XIAOMI_MIMO_API_KEY = os.getenv("XIAOMI_MIMO_API_KEY")
XIAOMI_MIMO_BASE_URL = os.getenv("XIAOMI_MIMO_BASE_URL")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# if XIAOMI_MIMO_MODEL:
#     print("Yes!")
# else:
#     print("No!")