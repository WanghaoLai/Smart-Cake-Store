"""LangChain tool catalog selection."""

from langchain_core.tools import BaseTool


def select_tools(catalog: list[BaseTool], names: list[str]) -> list[BaseTool]:
    """Select configured tools in whitelist order and reject invalid catalogs."""
    by_name = {item.name: item for item in catalog}
    if len(by_name) != len(catalog):
        raise ValueError("LangChain 工具名称必须唯一")
    missing = [name for name in names if name not in by_name]
    if missing:
        raise ValueError(f"Agent 配置了未注册工具: {', '.join(missing)}")
    return [by_name[name] for name in names]

__all__ = ["select_tools"]
