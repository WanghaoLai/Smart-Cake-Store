import asyncio
from .llm_service import LLMService
from .rag_service import RAGService
from models import Goods
from settings import AI_CONFIG


class ChatService:
    def __init__(self, llm_service: LLMService, rag_service: RAGService):
        self.llm = llm_service
        self.rag = rag_service
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

    async def process_message(self, user_message: str, history: list) -> str:
        """处理用户消息（非流式）"""
        context = await self._get_context(user_message)
        messages = self._build_messages(history, user_message, context)
        response = await self.llm.chat(messages, self.system_prompt)
        return response

    async def process_message_stream(self, user_message: str, history: list):
        """处理用户消息（流式）"""
        context = await self._get_context(user_message)
        messages = self._build_messages(history, user_message, context)

        async for chunk in self.llm.chat_stream(messages, self.system_prompt):
            yield chunk

    async def _get_context(self, query: str) -> str:
        """获取相关上下文"""
        # if self._need_rag(query):
        #     results = self.rag.search(query, top_k=3)
        #     if results:
        #         context = "以下是相关的商品信息：\n\n"
        #         for i, r in enumerate(results, 1):
        #             context += f"{i}. {r['content']}\n\n"
        #         return context
        return await self._direct_query(query)

    # def _need_rag(self, query: str) -> bool:
    #     """判断是否需要 RAG 检索"""
    #     rag_keywords = ['推荐', '有什么', '哪些', '介绍', '口味', '适合', '建议', '生日', '情侣', '送']
    #     return any(keyword in query for keyword in rag_keywords)

    async def _direct_query(self, query: str) -> str:
        """直接数据库查询"""
        goods = await Goods.filter(name__contains=query).first()
        if goods:
            return f"商品信息：{goods.name}，价格：{goods.price}元，描述：{goods.description}"
        return ""

    def _build_messages(self, history: list, user_message: str, context: str) -> list:
        """构建消息列表"""
        messages = []

        for msg in history[-6:]:
            messages.append({"role": msg['role'], "content": msg['content']})

        if context:
            user_content = f"{user_message}\n\n---\n参考信息：\n{context}"
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})
        return messages

# def direct_query(query: str) -> str:
#     """直接数据库查询"""
#     goods = Goods.filter(name__contains=query).first()
#     if goods:
#         return f"商品信息：{goods.name}，价格：{goods.price}元，描述：{goods.description}"
#     return ""

# if __name__ == "__main__":
#     direct_query(query="祝寿蛋糕")