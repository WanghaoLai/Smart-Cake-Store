from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from hello_agents import HelloAgentsLLM
from utils.env_utils import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL, XIAOMI_MIMO_MODEL, XIAOMI_MIMO_API_KEY, XIAOMI_MIMO_BASE_URL

load_dotenv("/agent/.env")


class MyLLM(HelloAgentsLLM):
    """一个自定义的LLM客户端，通过继承增加了对ModelScope的支持"""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "auto",
        **kwargs,
    ):
        # 检查provider是否为我们想处理的‘modelscope’
        if provider == "deepseek":
            print("正在使用自定义的 ModelScope Provider")
            self.provider = "deepseek"

            # 解析ModelScope的凭证
            self.api_key = api_key or DEEPSEEK_API_KEY
            self.base_url = base_url or DEEPSEEK_BASE_URL

            if not self.api_key:
                raise ValueError(
                    "Deepseek API key not found. Please set DEEPSEEK_API_KEY environment variable."
                )

            # 设置默认模型和其它参数
            self.model = model or DEEPSEEK_MODEL
            self.temperature = kwargs.get("temperature", 0.7)
            self.max_tokens = kwargs.get("max_tokens")
            self.timeout = kwargs.get("timeout", 60)

            # 使用获取的参数创建OpenAI客户端实例
            self._client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
            )

        else:
            # 如果不是deepseek，则完全使用父类的原始逻辑来处理
            super().__init__(
                model=XIAOMI_MIMO_MODEL,
                api_key=XIAOMI_MIMO_API_KEY,
                base_url=XIAOMI_MIMO_BASE_URL,
                provider=None,
                **kwargs,
            )

    def invoke(self, messages: list[dict[str, str]], **kwargs) -> str:
        """非流式对话"""
        # full_message = []
        # if system_prompt:
        #     full_message.append({"role": "system", "content": system_prompt})
        # full_message.append(messages)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=message,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

llm = MyLLM(provider="deepseek")
system_prompt = "你是一位python高级程序员，可以回答用户关于python编程的一切问题。"
message = [{"role": "user", "content": "你好，我是python初学者，我的名字叫张三，请介绍一下自己。"}]
response = llm.invoke(messages=message, system_prompt=system_prompt)
print(response)
