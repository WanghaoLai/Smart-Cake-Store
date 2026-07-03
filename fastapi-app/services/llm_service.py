import dashscope
from dashscope import Generation
from settings import AI_CONFIG

class LLMService:
    def __init__(self, api_key: str, model: str = "qwen-turbo"):
        dashscope.api_key = api_key
        self.model = model

    async def chat_stream(self, messages: list, system_prompt: str = None):
        """流式对话"""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = Generation.call(
            model=self.model, # LLM模型名称
            messages=full_messages, # system prompt + 对话历史 + 用户消息
            result_format='message',
            stream=True, # 启用流式输出
            incremental_output=True # 每个chunk只包含增量内容，也就是每个 chunk 只包含新生成的 token，不是累积全文
        )

        for chunk in response:
            if chunk.status_code == 200:
                content = chunk.output.choices[0].message.content
                yield content # 逐 token 传出

    async def chat(self, messages: list, system_prompt: str = None) -> str:
        """非流式对话"""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = Generation.call(
            model=self.model,
            messages=full_messages,
            result_format='message'
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        raise Exception(f"LLM 调用失败: {response.message}")

    def chat_llm(self, messages: list, system_prompt: str = None) -> str:
        """非流式对话"""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = Generation.call(
            model=self.model,
            messages=full_messages,
            result_format='message'
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        raise Exception(f"LLM 调用失败: {response.message}")

# llm_service = LLMService(
#     api_key=AI_CONFIG["dashscope_api_key"],
#     model=AI_CONFIG["model"]
# )
#
# system_prompt = "你是一位python高级程序员，可以回答用户关于python编程的一切问题。"
# message = [{"role": "user", "content": "你好，请介绍一下自己。"}]
# response = llm_service.chat_llm(messages=message, system_prompt=system_prompt)
# print(type(response))
# print(response)
