"""Routing policy reserved for the explicit LangGraph workflow.

The production builder currently delegates the model/tool loop to LangChain's
``create_agent``.  Keeping routing policy isolated makes the later migration a
replacement inside ``graph/`` rather than a system-wide rewrite.
"""

from agents.state import AgentState


def after_verification(state: AgentState) -> str:
    """Choose retry or response when explicit verification nodes are enabled."""
    return "responder" if state.get("verified", False) else "planner"


__all__ = ["after_verification"]
