# LangChain 应用级 Agent

本目录遵循一个最小定义：

```text
Agent = Model + Harness

Harness = System Prompt
        + Tools
        + Context
        + Memory
        + Grounding
        + Middleware
        + Application Guardrails
```

第一性原理不是为每个名词建立一层目录，而是保证每项运行职责有且只有一个实现位置。

## 精炼后的结构

```text
agents/
├── agent/
│   ├── harness.py       # Context、Memory、Harness 及 AgentComponents
│   ├── grounding.py     # 调用模型前的确定性 MySQL/知识证据
│   └── executor.py      # 应用 Guardrails、日志、错误边界和稳定调用接口
├── config/              # 版本化 Agent profile 与环境配置
├── tools/
│   ├── business.py      # LangChain 业务工具
│   ├── knowledge.py     # LangChain 知识检索工具
│   ├── product/         # 商品查询与回答校验
│   └── order/           # 当前用户订单查询及取消事务
├── rag/                 # ChromaDB 与索引同步基础设施
├── model.py             # Model 创建
├── prompt.py            # System Prompt 组装
└── factory.py           # 唯一组合根
```

## 组件映射

| 定义 | 实现 | 原因 |
|---|---|---|
| Model | `model.py` | 隔离 DashScope/OpenAI-compatible 配置 |
| System Prompt | profile + `prompt.py` | 业务规则版本化，运行约束集中追加 |
| Tools | `tools/` | 模型访问外部业务的受控边界 |
| Context | `agent/harness.py` | 服务端可信身份，不进入工具参数 schema |
| Memory | `agent/harness.py` | 数据库历史转换为有界 LangChain 消息 |
| Grounding | `agent/grounding.py` | 关键事实不依赖模型主动检索 |
| Middleware | `factory.py` | 重试和调用上限只在组合时声明一次 |
| Guardrails | `agent/executor.py` | 最终消息校验、商品事实校验和安全降级 |

## 依赖规则

```text
Chat API → factory → CustomerServiceAgent → LangChain runtime
                  ├── Model
                  └── Harness
                       ├── Prompt
                       ├── Tools → Product / Order repositories
                       ├── Context / Memory / Grounding
                       └── Middleware
```

- 只有 `factory.py` 负责完整装配并调用 LangChain `create_agent`。
- API 只调用 `CustomerServiceAgent.process_message`，不感知模型或工具实现。
- 工具从 profile 白名单按顺序选择，未知工具和重名工具会在启动时失败。
- `user_id` 由可信 Context 注入，模型无法覆盖。
- 实时商品、库存和订单事实以 MySQL 为准；ChromaDB 用于政策和语义检索。
- 取消订单同时进行当前消息意图校验、当前用户归属校验和数据库事务处理。
- LangChain 内部实现不属于应用架构；项目源码不直接依赖 LangGraph。

## 扩展原则

新增应用级 Agent 时，新增 profile 和 factory 装配函数，并复用 `AgentComponents` / `CustomerServiceAgent`。只有在产生真实差异时才新增组件实现，例如不同 Memory 策略或不同 Grounding 来源；不为未来假设预建空目录、抽象类或转发模块。

新增工具必须同时更新：类型化工具、profile 白名单、system prompt 决策规则以及权限或副作用测试。

## 验证

```bash
cd fastapi-app
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```
