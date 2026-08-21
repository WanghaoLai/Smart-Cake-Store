# smart-cake-store · 智能商城导购与运营平台

> 一套可直接商用的蛋糕店 B2C 线上商城：Vue3 商城前台 + 管理后台，FastAPI 后端，内置基于 LangChain + ChromaDB 的接地式（Grounded）智能客服——商品问答有据可查，订单状态一句话直达。

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.124-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?logo=mysql&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.3-1C3C3C?logo=langchain&logoColor=white)

## 为什么需要这个项目

传统蛋糕店依赖手写订单和外卖平台，容易漏单错单、无法沉淀客户数据、常见咨询（尺寸、价格、配送范围）全靠人工逐条回复。本项目把这些环节搬到一套自有平台上：**线上展示 → 加购下单 → 支付（模拟）→ 制作配送 → 评价收藏** 全链路闭环，并用一个"只基于店内真实数据回答"的智能客服替代重复性人工咨询。

## 核心功能

**商城前台（用户角色）**

| 模块 | 说明 |
|------|------|
| 系统首页 | 公告轮播、商品推荐、分类快捷入口 |
| 导购商城 | 按分类浏览、搜索、查看详情与规格 |
| 订单 | 下单、模拟支付、订单状态跟踪、历史订单 |
| 收藏 / 评价 | 收藏心仪蛋糕，对已完成订单评价 |
| 收货地址 | 省市区级联地址管理、默认地址 |
| 智能客服 | 多轮对话（SSE 流式输出），可查询商品、库存、订单并推荐 |

**管理后台（管理员角色）**

| 模块 | 说明 |
|------|------|
| 数据统计 | 销量、订单、用户维度看板（`/stats` 接口） |
| 商品管理 | 分类管理、商品上下架、规格与价格维护 |
| 订单管理 | 全店订单查看与状态流转（待发货 → 已发货 → 待评价 → 已评价；待发货/已发货可取消并自动恢复库存） |
| 用户 / 管理员管理 | 账号查询、禁用、密码重置 |
| 公告 / 评价管理 | 首页公告发布，商品评价审核 |
| 知识库管理 | 上传 PDF/Word 知识文档，供智能客服检索 |

**智能客服（核心亮点）**

- 配置驱动的单 Agent（LangChain `create_agent`），提示词与工具白名单在 `fastapi-app/agents/config/customer_service.json` 中维护
- 回答前先做确定性取证（Grounding）：结合 MySQL 商品事实与 ChromaDB 知识库检索，LLM 不编造商品信息
- 5 个业务工具：知识检索、订单查询、取消订单（校验本人身份）、商品推荐、库存查询
- 会话与消息持久化到 MySQL，按"角色 + 用户 ID"隔离；用户身份由服务端注入，前端无法伪造

## 系统架构

```
┌──────────────────────────────────────────────┐
│        前端 vue/（Vue3 + Vite + Element Plus） │
│   登录/注册 · 商城前台 · 管理后台 · 客服对话     │
└───────────────┬──────────────────────────────┘
                │ HTTP / JSON（Axios + Bearer Token）
┌───────────────▼──────────────────────────────┐
│        后端 fastapi-app/（FastAPI + Tortoise） │
│  api/ 17 个路由模块（登录、商品、订单、客服…）    │
│  common/ JWT 鉴权 · 统一响应 · 异常映射          │
│  agents/ 智能客服（LangChain Agent + RAG）      │
└───────┬───────────────────────┬──────────────┘
        │                       │
   ┌────▼─────┐           ┌─────▼──────┐
   │ MySQL 8+ │           │  ChromaDB  │
   │ 业务数据   │           │ 知识向量索引 │
   └──────────┘           └────────────┘
```

智能客服一次问答的数据链路：

```
API 鉴权 → Grounding 确定性取证（MySQL + ChromaDB）
        → LangChain Agent 推理 / 可选工具调用
        → 商品事实校验 → SSE 流式返回最终回答
```

依赖方向约束（由 `tests/test_architecture.py` 强制保证）：

- `main.py → api、common、settings`；`api → agents、common、models`
- agents 核心执行器禁止导入 FastAPI 路由；前端只通过 HTTP API 访问后端

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.10 | 后端运行时 |
| Node.js | ≥ 18（含 npm） | 前端构建 |
| MySQL | ≥ 8.0 | 字符集 utf8mb4 |
| mysql 客户端 | 任意近期版本 | `migrate.sh` 依赖；macOS 默认不在 PATH 时用 `MYSQL_BIN` 指定 |
| DashScope API Key | 可选 | 智能客服必需；商城交易功能不依赖它 |

## 快速开始

最短路径：5 条命令 + 1 个启动脚本，约 10 分钟跑通。

```bash
# 1. 克隆项目
git clone <仓库地址> && cd samrt_cake_store

# 2. 配置环境变量（生成 JWT 密钥的命令见下方表格）
cp fastapi-app/.env.example fastapi-app/.env
#    编辑 fastapi-app/.env，至少填写 DB_PASSWORD 和 JWT_SECRET_KEY

# 3. 初始化数据库（幂等：自动建库导数据、执行增量迁移）
./migrate.sh

# 4. 安装依赖
python3 -m venv fastapi-app/.venv && fastapi-app/.venv/bin/pip install -r fastapi-app/requirements.txt
cd vue && npm install && cd ..

# 5. 一键启动前后端（macOS 可直接双击该脚本）
./一键启动.command
```

启动成功后脚本会自动打开浏览器。用以下演示账号登录（首次登录会自动把明文密码升级为 bcrypt 哈希）：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `222` | `222` |
| 用户 | `234` | `234` |

> 没有账号也可以在登录页点击注册，创建用户角色账号。种子数据中的 `admin` 账号密码为哈希值，仓库内无明文记录。
>
> **默认密码策略**：管理员在后台新建用户/管理员且不填密码时，默认密码为 `123`（管理员为 `admin`）。该账号会被标记 `must_change_password=True`，首次登录强制跳转改密页，不改密无法使用系统——上线前请确认此闭环未被移除，或改为随机密码一次性下发给使用者。

一键启动脚本默认后端 `127.0.0.1:9090`、前端 `127.0.0.1:5173`，端口被占用时自动顺延；日志写入 `logs/startup_<时间戳>/`（`logs/latest` 软链接指向最近一次）。按 `Ctrl+C` 同时停止前后端。

### 手动启动（分步）

如果你不用 macOS 或想单独控制进程：

```bash
# 后端（端口 9090，热重载）
cd fastapi-app
source .venv/bin/activate
python main.py
# 等价命令：uvicorn main:app --host 127.0.0.1 --port 9090

# 前端（新终端；VITE_BASE_URL 指向后端，必须在启动时提供）
cd vue
VITE_BASE_URL=http://127.0.0.1:9090 npm run dev
```

## 使用示例

### 界面操作

1. 打开 `http://127.0.0.1:5173`，在登录页选择身份（用户 / 管理员）并登录。
2. 用户角色：左侧菜单进入"导购商城"浏览下单，或点击"智能客服"提问，例如"有没有草莓味的蛋糕？""我的订单到哪了？"。
3. 管理员角色：在"商品管理"上架新品后，前台立即可见；在"知识库管理"上传店铺说明文档，客服回答会自动引用。

### API 调用（curl）

统一响应格式为 `{"code": "200", "msg": "请求成功", "data": ...}`，鉴权使用 `Authorization: Bearer <token>` 头。

```bash
BASE=http://127.0.0.1:9090

# 1. 登录，从返回中取出 token
curl -s -X POST $BASE/login \
  -H "Content-Type: application/json" \
  -d '{"username": "234", "password": "234", "role": "用户"}'
# → {"code":"200","msg":"请求成功","data":{"token":"eyJ...","user":{...}}}

TOKEN=<上一步返回的 token>

# 2. 创建客服会话
curl -s -X POST $BASE/chat/conversation -H "Authorization: Bearer $TOKEN"
# → {"code":"200","msg":"请求成功","data":{"id":1,"title":"新对话"}}

# 3. 发送消息（SSE 流式返回）
curl -N -X POST $BASE/chat/send \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"conversation_id": 1, "message": "有什么草莓味的蛋糕？推荐一款"}'
```

主要 API 模块（完整清单见 `fastapi-app/api/`）：

| 前缀 | 鉴权 | 职责 |
|------|------|------|
| `/login` `/register` | 公开 | 登录（按角色分流用户/管理员）、注册 |
| `/goods` `/category` | 登录用户 | 商品与分类的查询、管理 |
| `/orders` | 登录用户 | 下单、状态流转、订单查询 |
| `/chat` | 登录用户 | 会话管理、SSE 消息、向量索引重建 |
| `/knowledge` | 管理员 | 知识文档上传与索引统计 |
| `/user` `/admin` | 管理员 | 用户与管理员账号管理 |
| `/files` `/region` `/address` `/favorite` `/reviews` `/notice` `/stats` `/health` | 按模块 | 文件、省市区、地址、收藏、评价、公告、统计、健康检查 |

## 目录结构

```
samrt_cake_store/
├── 一键启动.command              # 前后端一键启动（端口探测、日志、自动开浏览器）
├── migrate.sh                    # 幂等数据库迁移执行器
├── cake_store.sql                # 基础 schema + 种子数据（全量 dump）
├── migrations/                   # 增量迁移 SQL（附 README 说明执行规则）
├── logs/                         # 启动日志（运行时生成，不入库）
│
├── fastapi-app/                  # 后端
│   ├── main.py                   # 应用入口：中间件、路由注册、ORM
│   ├── settings.py               # 环境变量与数据库配置（含 JWT 强度校验）
│   ├── models.py                 # Tortoise ORM 业务模型
│   ├── .env.example              # 环境变量模板
│   ├── api/                      # 17 个 HTTP 路由模块（只做鉴权与协议）
│   ├── agents/                   # 智能客服（唯一智能模块）
│   │   ├── config/               # Agent 配置与提示词/工具白名单 JSON
│   │   ├── agent/                # 执行器、上下文、Grounding、记忆
│   │   ├── model/                # 通义千问 OpenAI 兼容适配器
│   │   ├── knowledge/            # 文档解析、Embedding、ChromaDB 同步
│   │   └── tools/                # LangChain 业务工具
│   ├── common/                   # JWT、密码哈希、统一响应、异常处理
│   ├── core/                     # 基础配置与数据库连接
│   ├── tests/                    # 回归测试（Agent、工具、API、架构约束）
│   ├── chroma_db/                # 向量索引（可重建，不入库）
│   └── files/                    # 上传文件（不入库）
│
└── vue/                          # 前端（单一 SPA，商城与管理后台共用）
    ├── vite.config.js            # Vite + Element Plus 按需引入
    └── src/
        ├── router/               # 路由与登录守卫
        ├── utils/request.js      # Axios 封装（baseURL 取 VITE_BASE_URL）
        └── views/                # 登录/注册 + manager/ 下 16 个业务页面
```

## 数据库与迁移

`migrate.sh` 的工作流：读取 `fastapi-app/.env` 连接信息 → 若 `orders` 表不存在则导入 `cake_store.sql` → 按文件名升序执行 `migrations/*.sql`，已应用的自动跳过。全程强制 utf8mb4，可安全重跑。

### 数据表一览

`cake_store` 库共 16 张业务表 + 1 张迁移记录表，与 `fastapi-app/models.py` 的 Tortoise 模型一一对应：

| 表 | 对应模型 | 说明 |
|----|----------|------|
| `admin` / `user` | Admin / User | 管理员与用户独立建表，数字主键可能重叠；业务归属一律用「角色 + 用户 ID」联合判定 |
| `category` / `goods` | Category / Goods | 分类与商品；`goods` 含配料/规格/保质期等详情列与库存 `num`（实时事实以 MySQL 为准） |
| `tb_province` / `tb_city` / `tb_town` | Province / City / Town | 只读三级区划基础数据 |
| `address` | Address | 收货地址；冗余省市区名称避免三表 join，每用户至多 1 条默认地址 |
| `orders` | Orders | 订单；状态机：待发货（默认）→ 已发货 → 待评价 → 已评价，待发货/已发货可取消（历史数据"已签收"视同"待评价"，代码兼容） |
| `review` | Review | 商品评价；`order_id` 唯一约束保证 1 单 1 评，`images` 存 JSON 数组字符串 |
| `favorite` | Favorite | 商品收藏 |
| `notice` | Notice | 首页公告 |
| `conversation` / `message` | Conversation / Message | 客服会话与消息；`idx_conversation_owner (owner_role, user_id)` 联合索引隔离不同角色会话 |
| `knowledge` | Knowledge | RAG 知识文档元数据；文档内容向量化存于 ChromaDB，原文不落盘 |
| `index_task` | IndexTask | 商品 → 向量索引同步 outbox；业务事务只写本表，后台异步同步 ChromaDB，失败重试 3 次 |
| `_schema_migrations` | — | `migrate.sh` 的迁移执行记录；基础 dump 已预置 001–003，全新部署导入后自动跳过对应迁移 |

种子数据说明：初始公告已使用「智能商城导购与运营平台」名称；演示账号 `222`/`234` 为明文密码，首次登录自动升级为 bcrypt 哈希。

新增表结构变更时：

1. 在 `migrations/` 下新建 `NNN_描述.sql`（编号递增），只写增量 DDL。
2. 本地执行 `./migrate.sh` 验证。
3. 不要手动修改 `cake_store.sql`——它包含 `DROP TABLE`，对已有数据手工重跑会清库（执行器已内置防重入保护）。

迁移设计细节见 [migrations/README.md](migrations/README.md)。

## 配置参考

所有配置通过 `fastapi-app/.env` 提供，模板见 [fastapi-app/.env.example](fastapi-app/.env.example)。

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` | 是 | `localhost` / `3306` / `cake_store` / `root` | MySQL 连接 |
| `DB_PASSWORD` | 是 | — | `migrate.sh` 未配置会直接退出 |
| `JWT_SECRET_KEY` | 是 | — | 启动时强制校验：开发 ≥16 字符，生产（`APP_ENV=production`）≥32 字符，否则拒绝启动 |
| `DASHSCOPE_API_KEY` | 智能客服需要 | — | [控制台获取](https://dashscope.console.aliyun.com/apiKey)；未配置时商城正常，客服返回"暂时不可用" |
| `LLM_MODEL` / `EMBEDDING_MODEL` | 否 | `qwen-turbo` / `text-embedding-v2` | 通义千问模型选择 |
| `APP_ENV` | 否 | `development` | `production` 时 CORS 只放行白名单 |
| `CORS_ORIGINS` | 生产必改 | localhost:5173 | 允许的前端来源，逗号分隔 |
| `JWT_EXPIRE_HOURS` | 否 | `2` | Token 有效期（小时） |

生成强随机密钥：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 测试与验证

```bash
# 后端回归测试（无需数据库）
PYTHONPATH=fastapi-app python3 -m unittest discover -s fastapi-app/tests -v

# 前端构建验证
cd vue && npm run build
```

后端测试覆盖：Agent 协议与边界、LangChain 工具调用、Grounding 取证、订单工具、聊天 API，以及架构约束（路由唯一、CORS 不放开全源、提示词覆盖全部白名单工具等）。

## 生产部署要点

- `APP_ENV=production`，并提供 ≥32 字符的 `JWT_SECRET_KEY` 与真实域名的 `CORS_ORIGINS`
- 前端构建时注入后端地址：`VITE_BASE_URL=https://<后端域名> npm run build`，产物在 `vue/dist/`，由 Nginx 等静态服务器托管并反代 `/login`、`/goods` 等 API 路径到 uvicorn
- 后端多进程：`uvicorn main:app --host 127.0.0.1 --port 9090 --workers 4`（会话状态在 MySQL，无本地粘滞）
- 上传目录 `fastapi-app/files/` 需持久化；`chroma_db/` 丢失后可调 `POST /chat/rebuild-index` 重建

## 文档指引

| 文档 | 内容 |
|------|------|
| [智能商城导购与运营平台-完整开发方案.md](智能商城导购与运营平台-完整开发方案.md) | 需求分析、数据库设计、API 规划、30 天开发计划（注意：部分目录规划与当前代码有差异，以代码为准） |
| [项目整体架构.txt](项目整体架构.txt) | 当前实际代码的文件架构、依赖方向与验证命令 |
| [migrations/README.md](migrations/README.md) | 迁移文件结构与执行规则 |
| [fastapi-app/.env.example](fastapi-app/.env.example) | 全部环境变量及注释 |

## 参与贡献

1. 从 `main` 拉出特性分支开发（`git checkout -b feat/xxx`）。
2. 改动后端时运行 `PYTHONPATH=fastapi-app python3 -m unittest discover -s fastapi-app/tests -v`，全部通过再提交；涉及表结构的变更必须附带 `migrations/NNN_*.sql` 增量迁移。
3. 提交信息使用中文祈使句概述变更，例如"修复智能助手工具调用失败的问题"。
4. 不要提交 `.env`、`chroma_db/`、`files/`、`node_modules/`、`dist/`（`.gitignore` 已覆盖，克隆后按快速开始重建）。
5. 架构约束（路由注册方式、agents 目录依赖方向）由测试强制，重构前先阅读 [项目整体架构.txt](项目整体架构.txt) 中的"禁止事项"。

## 许可证

本项目暂未声明开源许可证，默认保留所有权利。如需开源或商用授权，请先联系仓库所有者补充 LICENSE 文件。
