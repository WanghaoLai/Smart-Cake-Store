import re
from .llm_service import LLMService
from .knowledge_service import KnowledgeService
from .customer_service_tools import TOOLS_MAP, TOOL_DEFINITIONS
from settings import AI_CONFIG


class ChatService:
    def __init__(self, llm_service: LLMService, knowledge_service: KnowledgeService = None):
        self.llm = llm_service
        self.knowledge = knowledge_service or KnowledgeService()
        self.system_prompt = f"""你是 Little-bear Cake Store 的智能客服助手。

你的职责：
1. 回答用户关于蛋糕商品的问题（口味、价格、描述等）
2. 帮助用户查询订单状态
3. 推荐合适的蛋糕产品
4. 查询蛋糕库存
5. 帮助用户取消订单
6. 解答其他与蛋糕店相关的问题

## 可用工具
当需要查询实时数据时，使用以下格式调用工具：
`[TOOL_CALL:tool_name:key1=value1,key2=value2]`

{TOOL_DEFINITIONS}

工具调用示例：
- 查所有订单：[TOOL_CALL:get_order_status:]
- 按ID查订单：[TOOL_CALL:get_order_status:order_id=1]
- 按单号查订单：[TOOL_CALL:get_order_status:order_no=202607041430221234]
- 按ID取消订单：[TOOL_CALL:cancel_order:order_id=1]
- 按单号取消订单：[TOOL_CALL:cancel_order:order_no=202607041430221234]
- 推荐蛋糕：[TOOL_CALL:recommend_cake:preference=生日]
- 查库存：[TOOL_CALL:check_stock:goods_name=草莓蛋糕]

工具调用结果会自动返回，然后你基于结果回答用户。调用工具时只用 [TOOL_CALL:...] 格式，不要添加其他文字。

回答要求：
- 友好、专业、简洁
- 当消息中包含"参考信息"时，优先基于参考信息中的知识库内容回答
- 基于工具返回的真实信息回答
- 如果不确定，诚实告知用户
- 适当使用 emoji 增加亲和力"""

    async def process_message(self, user_message: str, history: list, user_id: int = None) -> str:
        """处理用户消息（非流式）"""
        context = self._get_rag_context(user_message)
        messages = self._build_messages(history, user_message, context)
        response = await self.llm.chat(messages, self.system_prompt)
        return await self._handle_tool_calls(response, messages, user_id)

    async def process_message_stream(self, user_message: str, history: list, user_id: int = None):
        """处理用户消息（流式），RAG 上下文 + 工具结果合并注入"""
        rag_context = self._get_rag_context(user_message)
        messages = self._build_messages(history, user_message, rag_context)

        first_response = await self.llm.chat(messages, self.system_prompt)

        tool_calls = self._parse_tool_calls(first_response)
        if tool_calls:
            tool_results = []
            for tool_name, params_str in tool_calls:
                result = await self._execute_tool(tool_name, params_str, user_id)
                tool_results.append(result)

            messages.append({"role": "assistant", "content": "正在查询数据..."})
            messages.append({"role": "user", "content": self._format_tool_response(tool_results, rag_context)})

            async for chunk in self.llm.chat_stream(messages, self.system_prompt):
                yield chunk
        else:
            for char in first_response:
                yield char

    def _get_rag_context(self, query: str) -> str:
        """从 ChromaDB 知识库和商品向量库检索相关上下文"""
        try:
            results = self.knowledge.search(query, top_k=3)
            if not results:
                return ""

            doc_parts = []
            goods_parts = []
            for r in results:
                if r.get("source") == "goods_base":
                    goods_parts.append(f"- {r['content']}")
                else:
                    doc_parts.append(f"- {r['content']}")

            context = ""
            if goods_parts:
                context += "相关商品信息：\n" + "\n".join(goods_parts) + "\n\n"
            if doc_parts:
                context += "相关知识库信息：\n" + "\n".join(doc_parts) + "\n\n"
            return context.strip()
        except Exception:
            pass
        return ""

    def _parse_tool_calls(self, text: str) -> list:
        """解析 [TOOL_CALL:name:params] 格式"""
        pattern = r"\[TOOL_CALL:([^:\[\]]+):([^\[\]]*)\]"
        matches = re.findall(pattern, text)
        return [(name.strip(), params.strip()) for name, params in matches]

    async def _execute_tool(self, tool_name: str, params_str: str, user_id: int = None) -> str:
        """执行工具调用"""
        if tool_name not in TOOLS_MAP:
            return f"未知工具 {tool_name}，可用工具：{', '.join(TOOLS_MAP.keys())}"

        params = {}
        if params_str:
            for pair in params_str.split(","):
                pair = pair.strip()
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    params[key.strip()] = value.strip()

        if user_id is not None and tool_name in ("get_order_status", "cancel_order"):
            params["user_id"] = user_id

        func = TOOLS_MAP[tool_name]
        try:
            result = await func(**params)
            return f"[{tool_name}] 执行结果：\n{result}"
        except Exception as e:
            return f"[{tool_name}] 执行失败：{str(e)}"

    async def _handle_tool_calls(self, response: str, messages: list, user_id: int = None) -> str:
        """处理工具调用并返回最终回答（非流式版本），RAG + 工具结果合并"""
        tool_calls = self._parse_tool_calls(response)
        if not tool_calls:
            return response

        tool_results = []
        for tool_name, params_str in tool_calls:
            result = await self._execute_tool(tool_name, params_str, user_id)
            tool_results.append(result)

        messages.append({"role": "assistant", "content": "正在查询数据..."})
        # RAG 上下文已在上游 _build_messages 时注入第一条 user message，
        # 这里提取最后一条 user message 中的 context 用于合并提示
        rag_context = self._extract_context_from_messages(messages)
        messages.append({"role": "user", "content": self._format_tool_response(tool_results, rag_context)})

        return await self.llm.chat(messages, self.system_prompt)

    def _extract_context_from_messages(self, messages: list) -> str:
        """从消息列表中提取 RAG 上下文（位于最后一条 user message 的 '参考信息：' 之后）"""
        for msg in reversed(messages):
            if msg.get("role") == "user" and "参考信息：" in msg.get("content", ""):
                parts = msg["content"].split("参考信息：", 1)
                return parts[1].strip() if len(parts) > 1 else ""
        return ""

    def _format_tool_response(self, tool_results: list, rag_context: str = "") -> str:
        """格式化工具执行结果，与 RAG 上下文合并引导 LLM 综合回答"""
        msg = f"工具执行结果：\n{chr(10).join(tool_results)}\n\n"
        if rag_context:
            msg += (
                "另外，以下是之前检索到的参考信息，可能对回答有帮助：\n"
                f"{rag_context}\n\n"
            )
        msg += "请综合以上工具查询结果和参考信息，完整、准确地回答用户的问题。"
        return msg

    def _build_messages(self, history: list, user_message: str, context: str = "") -> list:
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
