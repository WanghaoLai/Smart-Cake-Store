import unittest
from pathlib import Path

from agents.factory import create_customer_service_agent
from agents.rag.vector_store import CHROMA_PATH
from main import app
from starlette.middleware.cors import CORSMiddleware


BACKEND_DIR = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_legacy_intelligence_directory_is_removed(self):
        self.assertFalse((BACKEND_DIR / "services").exists())

    def test_routes_are_unique_and_public_contracts_are_preserved(self):
        paths = [route.path for route in app.routes]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue({
            "/login",
            "/register",
            "/updatePassword",
            "/chat/send",
            "/chat/rebuild-index",
            "/chat/index/run-pending",
            "/chat/index/stats",
            "/knowledge/upload",
            "/goods/add",
        }.issubset(paths))

    def test_agent_tool_order_matches_profile_whitelist(self):
        agent = create_customer_service_agent()
        self.assertEqual([tool.name for tool in agent.tools], agent.profile.tools)
        self.assertEqual(agent.framework, "langchain")
        self.assertTrue(callable(agent.runtime.ainvoke))

    def test_application_agent_exposes_model_and_harness_components(self):
        agent = create_customer_service_agent()
        self.assertIsNotNone(agent.components.model)
        self.assertEqual(agent.components.harness.tools, tuple(agent.tools))
        self.assertTrue(agent.components.harness.system_prompt)
        self.assertIsNotNone(agent.components.harness.memory)
        self.assertIsNotNone(agent.components.harness.grounding)
        self.assertEqual(len(agent.components.harness.middleware), 3)

    def test_agents_do_not_directly_depend_on_langgraph(self):
        self.assertFalse((BACKEND_DIR / "agents" / "graph").exists())
        source_files = (BACKEND_DIR / "agents").rglob("*.py")
        direct_imports = [
            str(path.relative_to(BACKEND_DIR))
            for path in source_files
            if "langgraph" in path.read_text(encoding="utf-8").lower()
        ]
        self.assertEqual(direct_imports, [])
        requirements = (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("langgraph", requirements)

    def test_agents_tree_contains_no_compatibility_only_packages(self):
        obsolete = {"graph", "knowledge", "llm", "memory", "prompts", "security"}
        existing = {
            path.name
            for path in (BACKEND_DIR / "agents").iterdir()
            if path.is_dir() and path.name != "__pycache__"
        }
        self.assertFalse(existing & obsolete)

    def test_system_prompt_documents_every_whitelisted_tool(self):
        """决策树是模型选工具的唯一显式引导：白名单里的每个工具名都必须
        在 system_prompt 中至少出现一次，否则新增/重命名工具时漏写决策
        规则会让模型完全不知道何时调用它。把这条不变量固化为 CI 检查。
        """
        agent = create_customer_service_agent()
        prompt = agent.profile.system_prompt
        missing = [name for name in agent.profile.tools if name not in prompt]
        self.assertEqual(
            missing, [],
            f"system_prompt 决策树未覆盖以下白名单工具: {missing}；"
            f"请在 config/customer_service.json 的 system_prompt 中补充对应规则",
        )

    def test_chroma_data_location_did_not_move(self):
        self.assertEqual(Path(CHROMA_PATH), BACKEND_DIR / "chroma_db")

    def test_cors_does_not_allow_every_origin(self):
        cors = next(item for item in app.user_middleware if item.cls is CORSMiddleware)
        self.assertNotIn("*", cors.kwargs["allow_origins"])
        self.assertNotIn("*", cors.kwargs["allow_methods"])
        self.assertNotIn("*", cors.kwargs["allow_headers"])


if __name__ == "__main__":
    unittest.main()
