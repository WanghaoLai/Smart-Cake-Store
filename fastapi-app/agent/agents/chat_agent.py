# 将所有节点连接起来，构建图
import asyncio
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from utils.chat_utils import ChatAgentState
from tools.chat_tools import understand_query_node, database_search_node, generate_answer_node

def create_search_assistant():
    workflow = StateGraph(ChatAgentState)

    # 添加节点
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", database_search_node)
    workflow.add_node("answer", generate_answer_node)

    # 设置线性流程
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    # 编译图
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app

async def main():
    """主函数：运行智能搜索助手"""

    app = create_search_assistant()

    print("智能搜索助手启动！")
    print("我会基于数据库中商品信息为您提供最真实、可靠和准确的商品信息")
    print("(输入 'exit' 退出)\n")

    session_count = 0

    while True:
        user_input = input("请输入您要查询的商品名称：").strip()

        if user_input.lower() in ['quit', 'q', '退出', 'exit']:
            print("感谢使用！再见！")
            break

        if not user_input:
            continue

        session_count += 1
        config = {"configurable": {"thread_id": f"search-session-{session_count}"}}

        # 初始状态
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": "",
            "search_query": "",
            "search_results": "",
            "final_answer": "",
            "step": "start"
        }
        # print(initial_state["messages"])

        try:
            print("\n" + "="*60)

            # 执行工作流
            async for output in app.astream(initial_state, config=config):
                for node_name, node_output in output.items():
                    if "messages" in node_output and node_output["messages"]:
                        latest_message = node_output["messages"][-1]
                        if isinstance(latest_message, AIMessage):
                            if node_name == "understand":
                                print(f"理解阶段：{latest_message.content}")
                            elif node_name == "search":
                                print(f"搜索阶段：{latest_message.content}")
                            elif node_name == "answer":
                                print(f"\n最终回答：\n{latest_message.content}")
            print("\n" + "="*60)

        except Exception as e:
            print(f"发生错误：{e}")
            print("请重新输入您的问题。\n")

if __name__ == "__main__":
    asyncio.run(main())