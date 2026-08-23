智能商城导购与运营平台：项目文件架构
====================================

本文件描述当前实际代码，而不是未来规划。更新日期：2026-08-22。
系统由 FastAPI 后端、Vue 3 前端、两个配置驱动的 LangChain Agent（智能客服、
运营商品分析师）以及规则推荐 / 语义搜索模块组成。

项目根目录
----------

samrt_cake_store/
├── README.md                       项目入口文档（快速开始、API 示例、配置参考）
├── start.command                   macOS 前后端一键启动脚本
├── docs/                           项目文档（入库；README 与 db/README 链接到此）
│   ├── architecture.md             本文件：文件架构、依赖方向与验证命令
│   ├── code-review.md              21 项审查发现与逐项修复记录
│   ├── roadmap.md                  架构评审结论与 P0–P2 路线图
│   └── archive/                    本地归档：过时开发方案与历史规划（不入库）
├── db/                             数据库唯一入口（说明见 db/README.md）
│   ├── migrate.sh                  幂等迁移执行器（自动建库 + schema + 种子 + 增量）
│   ├── cake_store.sql              基础 schema（纯 DDL；001–011 已预标记）
│   ├── seed_base.sql               基础种子：演示账号 + 区划 + 分类公告（幂等）
│   └── migrations/                 增量迁移 001–011 + archive/ 历史留档
├── logs/                           启动日志（latest 软链接指向最近一次）
├── fastapi-app/                    FastAPI 后端
└── vue/                            Vue 3 + Vite 前端

后端 fastapi-app/
-----------------

fastapi-app/
├── main.py                         应用创建、CORS、路由与 ORM 注册
├── settings.py                     环境变量与数据库配置（JWT 强度校验、
│                                   限流与语义搜索参数）
├── models.py                       Tortoise ORM 业务模型
├── requirements.txt                Python 依赖
├── scripts/                        数据填充脚本（应用层数据工具）
│   ├── seed_goods.py               商品种子数据
│   └── seed_analysis_data.py       运营分析页演示数据填充（可选，见脚本注释）
│
├── api/                            HTTP 接口层；只处理鉴权、协议、持久化编排
│   ├── __init__.py                 显式装配全部 APIRouter（18 个模块）
│   ├── auth.py / auth_schemas.py   登录、注册、修改密码与请求协议
│   ├── chat.py                     会话、消息、SSE 输出与限流接入
│   ├── index.py                    向量索引重建、重试和状态接口
│   ├── goods.py                    商品管理、语义搜索入口与索引 outbox 写入
│   ├── ops.py                      运营分析：四维统计 + AI 分析 + 报告回看
│   ├── stats.py                    首页看板（SQL 聚合）与个性化推荐接入
│   └── ...                         用户、管理员、订单、评价、收藏、公告、
│                                   地址、区划、文件、健康检查等业务接口
│
├── agents/                         唯一智能模块
│   ├── factory.py                  create_agent 生产装配入口（客服 + 分析师）
│   ├── model.py                    千问 OpenAI 兼容端点的 ChatOpenAI 适配器
│   ├── prompt.py                   系统提示词组装
│   ├── config/
│   │   ├── settings.py             Agent 环境配置读取
│   │   ├── customer_service.json   客服：身份、提示词、工具白名单与运行边界
│   │   └── ops_assistant.json      运营分析师：商品分析工具白名单
│   ├── agent/
│   │   ├── harness.py              组件装配、服务端可信上下文、有界会话记忆
│   │   ├── executor.py             LangChain 运行时与业务 API 的适配门面
│   │   └── grounding.py            回答前确定性收集 MySQL / ChromaDB 证据
│   ├── rag/
│   │   ├── vector_store.py         文档解析、Embedding 与 ChromaDB 双集合存储
│   │   └── index_tasks.py          MySQL 到 ChromaDB 的 outbox 同步（重试 3 次）
│   ├── tools/
│   │   ├── business.py             客服工具目录与白名单选择
│   │   ├── knowledge.py            知识库检索工具
│   │   ├── order/repository.py     订单查询 / 取消（强制本人归属 + 事务行锁）
│   │   └── product/                商品搜索 / 详情（含答案事实校验与重建）
│   ├── recommendation/
│   │   ├── semantic_search.py      语义搜索：向量召回 + 实时过滤 + 三级兜底
│   │   └── rule_engine.py          个性化推荐：收藏/购买/评分/热度加权规则
│   └── ops/
│       ├── analysis.py             商品四维分析（销量 / 评价 / 库存 / 绩效）
│       ├── insights.py             全店洞察统计
│       ├── tools.py                分析师 Agent 的 LangChain 分析工具
│       └── report.py               运营报告落库与回看
│
├── common/                         跨接口公共基础设施
│   ├── auth.py                     JWT、密码哈希、强度校验与鉴权依赖
│   ├── exception_handler.py        统一异常映射（字段级 422 细节）
│   ├── result.py                   统一响应结构与 Decimal 序列化
│   ├── pagination.py               分页 clamp（1..100）
│   └── rate_limit.py               进程内滑动窗口限流器（接口兼容 Redis 替换）
│
└── tests/                          后端回归测试（97 个用例）
    ├── test_agent_executor.py       Agent 协议、工具和边界测试
    ├── test_agent_tools.py          LangChain 原生工具调用测试
    ├── test_grounding.py            MySQL / ChromaDB 取证测试
    ├── test_architecture.py         路由、目录和关键装配约束
    ├── test_chat_api.py             聊天 API 测试
    ├── test_order_tools.py          订单工具测试
    ├── test_business_rules.py       业务规则集成测试（SQLite 内存）
    ├── test_recommendation.py       语义搜索与推荐引擎测试
    └── test_ops.py                  运营分析接口测试

前端 vue/
---------

vue/
├── package.json                    前端依赖与脚本
├── vite.config.js                  Vite、Vue 和 Element Plus 配置
├── public/                         公共静态资源
└── src/
    ├── main.js                     Vue 应用入口
    ├── App.vue                     根组件
    ├── router/                     页面路由与登录守卫
    ├── utils/request.js            Axios、Token 和错误处理
    ├── utils/fileUrl.js            上传文件相对路径 → 完整 URL 拼接
    ├── assets/                     样式与图片
    └── views/                      登录、注册 + manager/ 下 17 个业务页面
                                     （含 Ops.vue 运营分析页）

依赖方向
--------

1. main.py → api、common、settings
2. api → agents、common、models
3. agents/agent → LangChain Core、config
4. agents/factory → LangChain create_agent、model、rag、tools
5. agents/tools、agents/rag、agents/ops、agents/recommendation → models
6. Vue → HTTP API；前端不依赖后端内部模块

数据链路
--------

客服回答：
API 鉴权 → grounding 结合多轮上下文确定性取证 → LangChain Agent
推理 / 可选工具调用 → MySQL 商品事实校验 → SSE 最终回答。

语义搜索：
自然语言 → Embedding → ChromaDB 向量召回 → MySQL 实时库存 / 上架过滤
→ 向量分 × 热度排序（向量 → 关键词 → 热门三级兜底）。

运营分析：
SQL 聚合产出确定性事实 → 事实摘要由服务端注入 → 分析师 Agent 归纳结论
→ 结论与事实并列返回，报告落库 ops_report（LLM 不可用时 facts-only 降级）。

禁止事项
--------

禁止 agents 核心执行器导入 FastAPI 路由。禁止恢复旧 services 智能目录或
在 api/__init__.py 中放置接口业务。

运行时数据
----------

- fastapi-app/.env：本地密钥和连接参数，不提交 Git（模板为
  fastapi-app/.env.example）
- fastapi-app/chroma_db/：可重建向量索引，不提交 Git
- fastapi-app/files/：上传文件，不提交 Git
- logs/：一键启动脚本日志，不提交 Git
- node_modules/、dist/、__pycache__/：依赖或生成物，不提交 Git

验证命令
--------

后端（当前 97 个用例，无需外部数据库）：
PYTHONPATH=fastapi-app python3 -m unittest discover -s fastapi-app/tests -v

前端：
cd vue && npm run build

数据库迁移（幂等，可安全重跑；环境变量可临时覆盖目标库）：
DB_NAME=cake_store_test ./db/migrate.sh

开发启动：
./start.command
