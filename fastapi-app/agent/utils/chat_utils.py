from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

# 定义全局状态的数据结构
class ChatAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str # 用户的初始问题
    search_query: str # 经过提取关键词后的查询
    search_results: str # 查询之后得到的查询结果
    final_answer: str # 整合查询结果得到的最终返回答案
    step: str # 标记当前步骤

