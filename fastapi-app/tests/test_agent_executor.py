import unittest
from typing import cast
from unittest.mock import AsyncMock, patch

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from agents.agent import (
    AgentComponents,
    AgentHarness,
    AgentUnavailableError,
    ConversationMemory,
    CustomerServiceAgent,
)
from agents.agent.executor import AgentInvocation
from agents.agent.grounding import GroundingEvidence
from agents.config import AgentProfile


class FakeAgentRuntime:
    def __init__(self, answer="完成", result=None, error=None, usage=None, model="qwen-turbo"):
        self.answer = answer
        self.result = result
        self.error = error
        self.usage = usage
        self.model = model
        self.calls = []

    async def ainvoke(self, input_data, config=None, context=None):
        self.calls.append({"input": input_data, "config": config, "context": context})
        if self.error:
            raise self.error
        if self.result is not None:
            return self.result
        msg = AIMessage(content=self.answer)
        if self.usage is not None:
            msg.usage_metadata = self.usage
        if self.model is not None:
            msg.response_metadata = {"model_name": self.model}
        return {"messages": [*input_data["messages"], msg]}


def make_executor(runtime=None, max_history=2, configured=True, grounding_service=None):
    class EmptyGrounding:
        async def collect(self, message, user_id, history):
            return []

    profile = AgentProfile(
        name="test_agent",
        system_prompt="test prompt",
        tools=[],
        max_history=max_history,
        max_model_calls=3,
        max_tool_calls=2,
    )
    components = AgentComponents(
        model=cast(BaseChatModel, None),
        harness=AgentHarness(
            system_prompt="test prompt",
            tools=(),
            memory=ConversationMemory(max_history),
            grounding=grounding_service or EmptyGrounding(),
        ),
    )
    return CustomerServiceAgent(
        profile=profile,
        runtime=runtime or FakeAgentRuntime(),
        components=components,
        configured=configured,
    )


class CustomerServiceAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_invokes_runtime_with_bounded_langchain_messages_and_trusted_context(self):
        runtime = FakeAgentRuntime("已完成")
        executor = make_executor(runtime)
        history = [
            {"role": "user", "content": "old"},
            {"role": "tool", "content": "untrusted"},
            {"role": "assistant", "content": "recent"},
            {"role": "user", "content": "latest"},
        ]

        result = await executor.process_message(
            "now",
            history,
            user_id=7,
            conversation_id=11,
        )

        self.assertEqual(result, "已完成")
        call = runtime.calls[0]
        messages = call["input"]["messages"]
        self.assertEqual([type(item) for item in messages], [AIMessage, HumanMessage, HumanMessage])
        self.assertEqual([item.content for item in messages], ["recent", "latest", "now"])
        self.assertEqual(call["context"].user_id, 7)
        self.assertEqual(call["context"].conversation_id, 11)
        self.assertEqual(call["context"].user_message, "now")
        self.assertEqual(
            call["context"].recent_history,
            (("user", "old"), ("assistant", "recent"), ("user", "latest")),
        )

    async def test_model_credentials_are_checked_before_runtime_invocation(self):
        runtime = FakeAgentRuntime()
        executor = make_executor(runtime, configured=False)
        with self.assertRaises(AgentUnavailableError):
            await executor.process_message("hello", [])
        self.assertEqual(runtime.calls, [])

    async def test_runtime_failure_is_wrapped_without_exposing_provider_error(self):
        executor = make_executor(FakeAgentRuntime(error=RuntimeError("secret provider detail")))
        with self.assertRaisesRegex(AgentUnavailableError, "智能客服执行失败") as raised:
            await executor.process_message("hello", [])
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)

    async def test_invalid_or_empty_final_message_is_rejected(self):
        executor = make_executor(FakeAgentRuntime(result={"messages": [HumanMessage(content="hello")]}))
        with self.assertRaisesRegex(AgentUnavailableError, "未返回有效回答"):
            await executor.process_message("hello", [])

    async def test_usage_metadata_and_latency_are_captured_in_invocation(self):
        runtime = FakeAgentRuntime(
            "已完成",
            usage={"input_tokens": 120, "output_tokens": 45},
            model="qwen-turbo",
        )
        executor = make_executor(runtime)
        invocation = await executor.invoke("now", [], user_id=7, conversation_id=11)
        self.assertIsInstance(invocation, AgentInvocation)
        self.assertEqual(invocation.answer, "已完成")
        self.assertEqual(invocation.prompt_tokens, 120)
        self.assertEqual(invocation.completion_tokens, 45)
        self.assertEqual(invocation.model, "qwen-turbo")
        self.assertGreaterEqual(invocation.latency_ms, 0)

    async def test_missing_usage_metadata_defaults_to_zero(self):
        # DashScope 某些模型不返回 usage_metadata：缺省记 0，不抛异常
        runtime = FakeAgentRuntime("已完成", usage=None, model=None)
        executor = make_executor(runtime)
        invocation = await executor.invoke("hi", [])
        self.assertEqual(invocation.prompt_tokens, 0)
        self.assertEqual(invocation.completion_tokens, 0)
        self.assertEqual(invocation.model, "")

    async def test_public_stream_contains_only_final_answer(self):
        answer = "这是一段超过二十四个字符的最终回答，用于验证对外输出不会包含内部工具调用。"
        executor = make_executor(FakeAgentRuntime(answer))
        chunks = [chunk async for chunk in executor.process_message_stream("hello", [])]
        self.assertEqual("".join(chunks), answer)
        self.assertTrue(all(len(chunk) <= 24 for chunk in chunks))

    async def test_server_evidence_is_inserted_before_current_user_message(self):
        class FakeGrounding:
            async def collect(self, message, user_id, history):
                self.args = (message, user_id, history)
                return [GroundingEvidence("MySQL实时商品", "草莓蛋糕｜价格 ¥88｜库存 3个")]

        runtime = FakeAgentRuntime("已根据库存回答")
        grounding = FakeGrounding()
        executor = make_executor(runtime, grounding_service=grounding)
        with patch(
            "agents.agent.executor.rebuild_product_answer",
            new=AsyncMock(return_value="已根据库存回答"),
        ):
            await executor.process_message("草莓蛋糕还有货吗", [], user_id=7)

        messages = runtime.calls[0]["input"]["messages"]
        self.assertEqual(grounding.args, ("草莓蛋糕还有货吗", 7, []))
        self.assertEqual(len(messages), 2)
        self.assertIn("MySQL实时商品", messages[0].content)
        self.assertIn("价格 ¥88", messages[0].content)
        self.assertEqual(messages[1].content, "草莓蛋糕还有货吗")

    async def test_hallucinated_catalog_answer_is_replaced_with_verified_mysql_answer(self):
        class FakeGrounding:
            async def collect(self, message, user_id, history):
                return [GroundingEvidence("MySQL实时商品", "福寿安康祝寿蛋糕｜价格 ¥108")]

        runtime = FakeAgentRuntime("1. 经典红丝绒蛋糕 - ¥98（库存 12份）")
        executor = make_executor(runtime, grounding_service=FakeGrounding())
        with patch(
            "agents.agent.executor.rebuild_product_answer",
            new=AsyncMock(return_value="1. **福寿安康祝寿蛋糕** — ¥108（库存 5份）"),
        ):
            answer = await executor.process_message("送长辈", [], user_id=7)

        self.assertIn("福寿安康祝寿蛋糕", answer)
        self.assertNotIn("经典红丝绒蛋糕", answer)


if __name__ == "__main__":
    unittest.main()
