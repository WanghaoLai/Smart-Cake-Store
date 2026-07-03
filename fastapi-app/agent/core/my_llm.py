from utils.env_utils import DEEPSEEK_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from langchain.chat_models import init_chat_model

MyLLM = init_chat_model(
    model=DEEPSEEK_MODEL,
    model_provider="deepseek",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# response = MyLLM.invoke("Hello")
# print(type(response))
# print(response)


