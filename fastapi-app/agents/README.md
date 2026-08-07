# Agents 子系统

本目录按稳定职责而不是框架 API 划分。HTTP 层只依赖 `agent.py` 的执行接口；模型、工具、RAG 和图编排都从组合根 `graph/builder.py` 注入。这样后续将 LangChain `create_agent` 逐步替换为显式 LangGraph 节点时，不需要修改聊天 API 或业务仓储。

## 目录

```text
agents/
├── agent.py                 # 对应用暴露的稳定执行接口
├── state.py                 # 图状态与输入输出协议
├── context.py               # 服务端可信运行上下文
├── graph/
│   ├── builder.py           # 唯一组合根；当前生产图仍由 create_agent 构建
│   ├── routes.py            # 显式 LangGraph 条件路由占位
│   └── nodes/               # understand/planner/tool_executor/verifier/responder 占位
├── tools/
│   ├── registry.py          # 工具白名单选择
│   ├── registry_tools.py    # 当前 LangChain 类型化工具定义
│   ├── knowledge.py         # ChromaDB 检索工具
│   ├── product/             # 商品搜索与回答校验
│   └── order/               # 订单查询与事务操作
├── llm/factory.py           # 模型供应商适配与创建
├── prompts/                 # 系统、意图与回答提示词
├── memory/checkpointer.py   # 持久消息到有界模型上下文的适配
├── rag/                     # 确定性取证、向量存储与索引任务
├── security/                # 权限断言与工具风险分类
└── config/                  # 版本化 Agent 配置
```

`factory.py`、`knowledge/`、`tools/business*.py` 和 `tools/chroma_search.py` 是旧导入路径的薄兼容层，不承载业务实现。待调用方完成迁移后可单独移除。

## 依赖方向

```text
API → agent.py ← graph/builder.py
                  ├─ llm/
                  ├─ prompts/
                  ├─ tools/ → product/、order/
                  └─ rag/

state.py、context.py、security/ 不依赖图的具体实现。
```

基本约束：

- `graph/builder.py` 是唯一允许装配模型、工具、中间件和图的地方。
- `agent.py` 只负责请求生命周期、上下文、错误边界与最终响应，不创建具体依赖。
- 工具只能通过 `registry.py` 和配置白名单进入图。
- 商品和订单数据库操作分开；只读查询与有副作用操作保持可辨识。
- RAG 只提供证据，不能替代 MySQL 实时库存和订单事实。
- `user_id` 仅从服务端 `AgentContext` 注入，模型参数不能覆盖。

## LangGraph 渐进迁移

当前生产路径继续使用经过验证的 LangChain `create_agent`（底层是 `CompiledStateGraph`），保证系统行为不变。`state.py`、`graph/routes.py` 和 `graph/nodes/` 已定义扩展边界，但占位节点尚未接入生产图，也不会执行虚构逻辑。

后续可按 `understand → planner → tool_executor → verifier → responder` 顺序逐个实现和测试节点；每次只在 `graph/builder.py` 切换已验证的部分。

## 配置与验证

默认配置位于 `config/customer_service.json`。新增工具需要：定义类型化工具、加入工具目录、通过 `registry.py` 注册，并在配置的 `tools` 白名单与系统提示词决策树中声明。

```bash
PYTHONPATH=fastapi-app python3 -m unittest discover -s fastapi-app/tests -v
```
