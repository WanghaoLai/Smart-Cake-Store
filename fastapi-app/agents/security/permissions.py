"""Central permission predicates for agent operations."""

from agents.context import AgentContext


def require_authenticated_user(context: AgentContext) -> int:
    if context.user_id is None:
        raise PermissionError("当前登录身份无效")
    return context.user_id


__all__ = ["require_authenticated_user"]
