import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage

from agents.agent import AgentContext
from agents.tools import select_tools
from agents.tools.business import business_tools
from settings import APP_TIMEZONE


def runtime(
    message: str,
    recent_history: tuple[tuple[str, str], ...] = (),
) -> ToolRuntime[AgentContext]:
    return ToolRuntime(
        state={"messages": []},
        context=AgentContext(
            user_id=7,
            conversation_id=11,
            user_message=message,
            recent_history=recent_history,
        ),
        config={},
        stream_writer=lambda _: None,
        tool_call_id="test-call",
        store=None,
    )


class LangChainToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_langchain_agent_executes_native_tool_call_loop(self):
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
        runtime = create_agent(model, tools=[echo], context_schema=AgentContext)
        result = await runtime.ainvoke(
            {"messages": [{"role": "user", "content": "test"}]},
            context=AgentContext(user_id=7, conversation_id=11, user_message="test"),
        )

        tool_messages = [item for item in result["messages"] if isinstance(item, ToolMessage)]
        self.assertEqual(tool_messages[0].content, "user=7,value=cake")
        self.assertEqual(result["messages"][-1].content, "工具调用完成")

    def test_runtime_context_is_not_exposed_in_tool_schema(self):
        for item in business_tools():
            self.assertNotIn("runtime", item.args_schema.model_json_schema().get("properties", {}))

    async def test_current_time_uses_configured_timezone_and_exposes_offset(self):
        current_time_tool = next(
            item for item in business_tools() if item.name == "get_current_time"
        )
        fixed_now = datetime(2026, 8, 13, 10, 30, 45, tzinfo=ZoneInfo("Asia/Shanghai"))

        with patch("agents.tools.business.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            result = await current_time_tool.ainvoke({})

        mocked_datetime.now.assert_called_once_with(ZoneInfo(APP_TIMEZONE))
        self.assertIn("2026年08月13日 10:30:45", result)
        self.assertIn("星期四", result)
        self.assertIn(f"时区：{APP_TIMEZONE}（UTC+08:00）", result)
        self.assertIn("ISO 8601：2026-08-13T10:30:45+08:00", result)

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
        self.assertIn("尚未明确确认取消", result)

    async def test_cancel_order_accepts_confirmed_follow_up_for_same_order(self):
        cancel_tool = next(item for item in business_tools() if item.name == "cancel_order")
        confirmation_context = runtime(
            "确认",
            (("assistant", "请确认是否要取消订单 202608130001？"),),
        )
        with patch(
            "agents.tools.business.cancel_order",
            new=AsyncMock(return_value="订单 202608130001 已成功取消，草莓蛋糕库存已恢复。"),
        ) as cancel:
            result = await cancel_tool.coroutine(
                order_id=None,
                order_no="202608130001",
                runtime=confirmation_context,
            )

        cancel.assert_awaited_once_with(
            user_id=7,
            order_id=None,
            order_no="202608130001",
        )
        self.assertIn("已成功取消", result)
        self.assertIn("库存已恢复", result)

    async def test_cancel_order_rejects_confirmation_without_matching_prompt(self):
        cancel_tool = next(item for item in business_tools() if item.name == "cancel_order")
        result = await cancel_tool.coroutine(
            order_id=None,
            order_no="202608130001",
            runtime=runtime("确认", (("assistant", "订单 202608130002 当前待发货。"),)),
        )

        self.assertIn("尚未明确确认取消", result)

    async def test_cancel_order_rejects_negative_intent(self):
        cancel_tool = next(item for item in business_tools() if item.name == "cancel_order")
        result = await cancel_tool.coroutine(
            order_id=None,
            order_no="202608130001",
            runtime=runtime("先不要取消这个订单"),
        )

        self.assertIn("尚未明确确认取消", result)

    def test_order_identifiers_are_mutually_exclusive(self):
        cancel_tool = next(item for item in business_tools() if item.name == "cancel_order")
        with self.assertRaisesRegex(ValueError, "只能提供一个"):
            cancel_tool.args_schema(order_id=1, order_no="202608130001")


if __name__ == "__main__":
    unittest.main()
