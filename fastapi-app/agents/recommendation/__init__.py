"""推荐与语义搜索模块：复用既有向量基础设施，纯规则 + 向量，无 LLM。"""
from .rule_engine import recommend
from .semantic_search import search

__all__ = ["recommend", "search"]
