"""Composition root for the LangChain customer-service application Agent."""

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


__all__ = ["build_customer_service_components", "create_customer_service_agent"]
