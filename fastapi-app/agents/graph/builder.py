"""Composition root for the customer-service graph and its dependencies."""

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
)

from agents.agent import LangChainAgentExecutor
from agents.context import AgentContext
from agents.prompts.system import build_system_prompt
from agents.rag.retriever import GroundingService
from agents.config import load_agent_profile, settings
from agents.llm.factory import create_dashscope_model
from agents.rag import knowledge_service
from agents.tools.knowledge import create_chroma_search_tool
from agents.tools.registry import select_tools
from agents.tools.registry_tools import business_tools


def create_customer_service_agent() -> LangChainAgentExecutor:
    profile = load_agent_profile()
    model = create_dashscope_model(settings)
    catalog = [
        create_chroma_search_tool(knowledge_service, default_top_k=settings.rag_top_k),
        *business_tools(),
    ]
    tools = select_tools(catalog, profile.tools)
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt(profile),
        context_schema=AgentContext,
        middleware=[
            ModelRetryMiddleware(
                max_retries=settings.max_retries,
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
        ],
        name=profile.name,
    )
    return LangChainAgentExecutor(
        profile=profile,
        graph=graph,
        tools=tools,
        configured=bool(settings.api_key),
        grounding_service=GroundingService(knowledge_service, top_k=settings.rag_top_k),
    )
