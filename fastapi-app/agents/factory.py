"""Composition root for the LangChain customer-service application Agent."""

from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
)

from agents.agent import (
    AgentComponents,
    AgentContext,
    AgentHarness,
    ConversationMemory,
    CustomerServiceAgent,
    GroundingService,
)
from agents.config import AgentProfile, AgentSettings, load_agent_profile, settings
from agents.model import create_model
from agents.prompt import build_system_prompt
from agents.rag import knowledge_service
from agents.tools.knowledge import create_chroma_search_tool
from agents.tools import select_tools
from agents.tools.business import business_tools
from agents.ops.tools import NoGrounding, analysis_tools

OPS_PROFILE_PATH = Path(__file__).resolve().parent / "config" / "ops_assistant.json"


def build_customer_service_components(
    profile: AgentProfile,
    agent_settings: AgentSettings = settings,
) -> AgentComponents:
    """Build replaceable Agent components without coupling them to the HTTP API."""
    catalog = [
        create_chroma_search_tool(knowledge_service, default_top_k=agent_settings.rag_top_k),
        *business_tools(),
    ]
    tools = tuple(select_tools(catalog, profile.tools))
    harness = AgentHarness(
        system_prompt=build_system_prompt(profile),
        tools=tools,
        memory=ConversationMemory(profile.max_history),
        grounding=GroundingService(knowledge_service, top_k=agent_settings.rag_top_k),
        middleware=(
            ModelRetryMiddleware(
                max_retries=agent_settings.max_retries,
                initial_delay=0.5,
                max_delay=4.0,
                on_failure="error",
            ),
            ModelCallLimitMiddleware(
                run_limit=profile.max_model_calls,
                exit_behavior="end",
            ),
            ToolCallLimitMiddleware(
                run_limit=profile.max_tool_calls,
                exit_behavior="continue",
            ),
        ),
    )
    return AgentComponents(
        model=create_model(agent_settings),
        harness=harness,
    )


def create_customer_service_agent() -> CustomerServiceAgent:
    """Create the production Agent exclusively through LangChain public APIs."""
    profile = load_agent_profile()
    components = build_customer_service_components(profile)
    harness = components.harness
    runtime = create_agent(
        model=components.model,
        tools=list(harness.tools),
        system_prompt=harness.system_prompt,
        context_schema=AgentContext,
        middleware=list(harness.middleware),
        name=profile.name,
    )
    return CustomerServiceAgent(
        profile=profile,
        runtime=runtime,
        components=components,
        configured=bool(settings.api_key),
    )


def build_ops_components(
    profile: AgentProfile,
    agent_settings: AgentSettings = settings,
) -> AgentComponents:
    """运营分析 Agent 组件：复用客服 harness 骨架，差异点是工具集与取证策略。

    复用 CustomerServiceAgent 门面（README 扩展原则）；NoGrounding 见其 docstring。"""
    tools = tuple(select_tools(analysis_tools(), profile.tools))
    harness = AgentHarness(
        system_prompt=build_system_prompt(profile),
        tools=tools,
        memory=ConversationMemory(profile.max_history),
        grounding=NoGrounding(),
        middleware=(
            ModelRetryMiddleware(
                max_retries=agent_settings.max_retries,
                initial_delay=0.5,
                max_delay=4.0,
                on_failure="error",
            ),
            ModelCallLimitMiddleware(
                run_limit=profile.max_model_calls,
                exit_behavior="end",
            ),
            ToolCallLimitMiddleware(
                run_limit=profile.max_tool_calls,
                exit_behavior="continue",
            ),
        ),
    )
    return AgentComponents(
        model=create_model(agent_settings),
        harness=harness,
    )


def create_ops_agent() -> CustomerServiceAgent:
    """管理员商品分析 Agent：分析事实由专用工具按需提供。"""
    profile = load_agent_profile(OPS_PROFILE_PATH)
    components = build_ops_components(profile)
    harness = components.harness
    runtime = create_agent(
        model=components.model,
        tools=list(harness.tools),
        system_prompt=harness.system_prompt,
        context_schema=AgentContext,
        middleware=list(harness.middleware),
        name=profile.name,
    )
    return CustomerServiceAgent(
        profile=profile,
        runtime=runtime,
        components=components,
        configured=bool(settings.api_key),
    )


__all__ = [
    "build_customer_service_components",
    "build_ops_components",
    "create_customer_service_agent",
    "create_ops_agent",
]
