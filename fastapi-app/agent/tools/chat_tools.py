from tortoise import Tortoise

from models import Goods
from settings import TORTOISE_ORM
from utils.chat_utils import ChatAgentState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.my_llm import MyLLM

# from langchain_openai import ChatOpenAI

llm = MyLLM

# 根据用户输入提取关键词
def understand_query_node(state: ChatAgentState) -> dict:
    """步骤1-理解用户查询并得到查询关键词"""
    user_message = state["messages"][-1].content
    # print(user_message) # 祝寿蛋糕

    understand_prompt = f"""分析用户的查询："{user_message}
请完成一个任务：
1.请从用户的查询中得到关于蛋糕名称的关键字，该关键字用于在数据库中进行模糊查询来获取对应的蛋糕信息

输出格式：
查询词：[最佳查询关键字]
"""
    response = llm.invoke([SystemMessage(content=understand_prompt)])
    # response = llm.invoke()
    response_text = response.content

    # 解析LLM的输出，提取搜索关键词
    search_query = user_message # 默认使用原始查询
    if "查询词：" in response_text:
        search_query = response_text.split("查询词：")[1].strip()
    # print(search_query)

    return {
        "user_query": response_text,
        "search_query": search_query,
        "step": "understood",
        "messages": [AIMessage(content=f"查询关键词为：{search_query}")]
    }

# 通过关键词在数据库中进行检索
async def database_search_node(state: ChatAgentState) -> dict:
    """步骤2-通过关键词在数据库中对应表进行模糊查询"""
    search_query = state["search_query"]
    # print(search_query)

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        goods = await Goods.filter(name__icontains=search_query).first()
        if goods:
            search_results = f"商品信息：{goods.name}，价格：{goods.price}元，描述：{goods.description}"
            # print(search_results)
            return {
                "search_results": search_results,
                "step": "searched",
                "messages": [AIMessage(content="搜索完成！正在整理答案...")]
            }
        return {
            "search_results": f"搜索失败...",
            "step": "search_failed",
            "messages": [AIMessage(content="根据关键词查询不到该商品信息...")]
        }
    except Exception as e:
        return {
            "search_results": f"搜索失败：{e}",
            "step": "search_failed",
            "messages": [AIMessage(content="搜索遇到问题...")]
        }
    finally:
        await Tortoise.close_connections()

def generate_answer_node(state: ChatAgentState) -> dict:
    """步骤3-基于搜索结果生成最终答案"""
    if state["step"] == "search_failed":
        # 如果搜索失败，执行回退策略，基于LLM自身知识回答
        fallback_prompt = f"搜索API暂时不可用，请基于您的知识回答用户的问题：\n用户问题：{state["user_query"]}"
        response = llm.invoke([SystemMessage(fallback_prompt)])
    else:
        # 搜索成功，基于搜索结果生成答案
        answer_prompt = f"""基于以下搜索结果为用户提供完整、准确的答案：
用户问题：{state["user_query"]}
搜索结果：{state["search_results"]}
请综合搜索结果，提供准确、有用的回答..."""
        response = llm.invoke([SystemMessage(answer_prompt)])
    return {
        "final_answer": response.content,
        "step": "completed",
        "messages": [AIMessage(content=response.content)]
    }

