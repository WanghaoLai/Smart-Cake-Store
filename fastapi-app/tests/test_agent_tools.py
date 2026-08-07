import unittest

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage

from agents.agent.context import AgentContext
from agents.tools import select_tools
from agents.tools.business import business_tools


def runtime(message: str) -> ToolRuntime[AgentContext]:
    return ToolRuntime(
        state={"messages": []},
        context=AgentContext(user_id=7, conversation_id=11, user_message=message),
        config={},
        stream_writer=lambda _: None,
        tool_call_id="test-call",
        store=None,
    )


class LangChainToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_langchain_graph_executes_native_tool_call_loop(self):
        class ToolCallingModel(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        @tool
        async def echo(value: str, runtime: ToolRuntime[AgentContext]) -> str:
            """Echo a value together with trusted runtime identity."""
            return f"user={runtime.context.user_id},value={value}"

        model = ToolCallingModel(responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "echo", "args": {"value": "cake"}, "id": "call-1"}],
            ),
            AIMessage(content="工具调用完成"),
        ])
        graph = create_agent(model, tools=[echo], context_schema=AgentContext)
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": "test"}]},
            context=AgentContext(user_id=7, conversation_id=11, user_message="test"),
        )

        tool_messages = [item for item in result["messages"] if isinstance(item, ToolMessage)]
        self.assertEqual(tool_messages[0].content, "user=7,value=cake")
        self.assertEqual(result["messages"][-1].content, "工具调用完成")

    def test_runtime_context_is_not_exposed_in_tool_schema(self):
        for item in business_tools():
            self.assertNotIn("runtime", item.args_schema.model_json_schema().get("properties", {}))

    def test_configuration_whitelist_rejects_unknown_tool(self):
        with self.assertRaisesRegex(ValueError, "未注册工具"):
            select_tools(business_tools(), ["delete_everything"])

    async def test_cancel_order_requires_explicit_current_message_intent(self):
        cancel_tool = next(item for item in business_tools() if item.name == "cancel_order")
        result = await cancel_tool.coroutine(
            order_id=1,
            order_no=None,
            runtime=runtime("帮我看看订单 1"),
        )
        self.assertIn("没有在当前消息中明确要求取消", result)


if __name__ == "__main__":
    unittest.main()
