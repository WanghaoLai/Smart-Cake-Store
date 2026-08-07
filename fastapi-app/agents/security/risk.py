"""Side-effect risk classification for current and future tools."""

from enum import Enum


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    MUTATING = "mutating"
    UNKNOWN = "unknown"


_TOOL_RISKS = {
    "search_knowledge": RiskLevel.READ_ONLY,
    "get_order_status": RiskLevel.READ_ONLY,
    "recommend_cake": RiskLevel.READ_ONLY,
    "check_stock": RiskLevel.READ_ONLY,
    "cancel_order": RiskLevel.MUTATING,
}


def classify_tool_risk(tool_name: str) -> RiskLevel:
    return _TOOL_RISKS.get(tool_name, RiskLevel.UNKNOWN)


__all__ = ["RiskLevel", "classify_tool_risk"]
