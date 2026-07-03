import asyncio
from core.llm import MyLLM
from models import Goods
from services import LLMService
from tortoise import Tortoise
from settings import TORTOISE_ORM


class Chat:
    def __init__(self, llm: MyLLM):
        self.llm = llm
        self.system_prompt = """你是 Little-bear Cake Store 的智能客服助手。

你的职责：
1. 回答用户关于蛋糕商品的问题（口味、价格、描述等）
2. 帮助用户查询订单状态
3. 推荐合适的蛋糕产品
4. 解答其他与蛋糕店相关的问题

回答要求：
- 友好、专业、简洁
- 基于数据库中的真实信息回答
- 如果不确定，诚实告知用户
- 适当使用 emoji 增加亲和力

当用户询问商品信息时，你会收到相关的商品数据，请基于这些数据回答。"""

    async def process_message(self, user_message: str) -> str:
        """处理用户消息（非流式）"""
        goods_data = await self._get_context(user_message)
        messages = self._build_messages(user_message, goods_data)
        response = self.llm.invoke(messages, self.system_prompt)
        return response

    async def _get_context(self, query: str) -> str:
        """获取相关上下文"""
        return await self._direct_query(query)

    async def _direct_query(self, query: str) -> str:
        """数据库查询"""
        await Tortoise.init(config=TORTOISE_ORM)
        try:
            goods = await Goods.filter(name__contains=query).first()
            if goods:
                return f"商品信息：{goods.name}，价格：{goods.price}元，描述：{goods.description}"
            return "商品信息查询失败！"
        finally:
            await Tortoise.close_connections()

    def _build_messages(self, user_message: str, goods_data: str) -> list:
        """构建消息列表"""
        messages = []

        if goods_data:
            user_content = f"{user_message}\n\n---\n参考信息：\n{goods_data}"
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})
        return messages

chat = Chat(llm=MyLLM())
user_message = "祝寿蛋糕"
response = asyncio.run(chat.process_message(user_message))
print(response)
