# 智能蛋糕商城系统分析报告

> 生成日期：2026-08-24
> 分析视角：真实系统使用者 + 设计师
> 参照标准：成熟电商商城系统标准功能集

---

## 一、现状评估

### 系统概况

- **技术栈**：Vue 3 + Element Plus（前端）+ FastAPI + Tortoise ORM（后端）+ MySQL + ChromaDB
- **规模**：20 个数据库表、22 个 API 模块、19 条前端路由、2 个 LangChain Agent
- **角色模型**：管理员（运营管理）、用户（购物消费）
- **AI 基座**：DashScope（通义千问）+ ChromaDB 向量库 + 自研 RAG/Grounding 框架

### 已完成模块矩阵

| 维度 | 用户侧 | 管理侧 | 评分 |
|---|---|---|---|
| 认证与权限 | 注册 / 登录 / 改密 | 管理员 CRUD / 重置密码 | ★★★★☆ |
| 商品体系 | 浏览 / 详情 / 搜索 / 规格选择 | 分类 CRUD / 商品 CRUD | ★★★★☆ |
| 订单流程 | 下单 / 查看 / 取消 | 订单列表 / 状态流转 | ★★★★☆ |
| 支付体系 | 钱包充值（模拟支付） | — | ★★☆☆☆ |
| 评价体系 | 查看评价 / 提交评价 | 评价管理 / 商家回复 | ★★★★☆ |
| 个人中心 | 头像 / 资料 / 密码 / 收藏 / 地址 | — | ★★★★☆ |
| 站内通知 | 未读角标 / 已读 / 清空 | 发货 / 取消自动触发通知 | ★★★★☆ |
| AI 客服 | 流式对话 / 知识库检索 / 订单查询 / 蛋糕推荐 | — | ★★★★★ |
| AI 运营 | — | 销量 / 评价 / 库存 / 综合分析 / 报告生成 | ★★★★☆ |
| 公告 / 知识库 | — | 公告 CRUD / 知识库上传管理 | ★★★★☆ |
| RAG 基础设施 | — | 向量索引 / 异步同步 / ChromaDB | ★★★★☆ |
| 审计日志 | — | 仅后端写入，无前端查看入口 | ★☆☆☆☆ |

### 后端 API 接口清单

| 模块文件 | 路由前缀 | 核心端点 |
|---|---|---|
| `auth.py` | `/` | `POST /login`、`POST /register`、`PUT /updatePassword` |
| `admin.py` | `/admin` | 增删改查 / 重置密码 / 分页查询 |
| `user.py` | `/user` | 增删改 / 重置密码 / 分页查询 |
| `account.py` | `/account` | `PUT /profile`（个人资料更新） |
| `category.py` | `/category` | 增删改查 / 全量查询 |
| `goods.py` | `/goods` | 增删改查 / 搜索 / 详情 |
| `orders.py` | `/orders` | 下单 / 删除 / 状态流转 / 分页查询 |
| `reviews.py` | `/reviews` | 发表 / 按商品查询 / 管理员回复 / 分页 |
| `favorite.py` | `/favorite` | 添加 / 移除 / 列表 / 状态检查 |
| `address.py` | `/address` | 增删改查 / 设默认 / 省市区三级联动 |
| `wallet.py` | `/wallet` | 余额查询 / 充值 / 交易记录 |
| `notification.py` | `/notification` | 列表 / 未读数 / 单条已读 / 全部已读 / 清空 |
| `chat.py` | `/chat` | 会话 CRUD / 流式消息发送（SSE） |
| `notice.py` | `/notice` | 公告增删改查 |
| `knowledge.py` | `/knowledge` | 知识库上传 / 列表 / 删除 / 统计 |
| `stats.py` | `/stats` | 首页统计数据 |
| `ops.py` | `/ops` | 销量 / 评价 / 库存 / 综合分析 / AI 报告 |
| `region.py` | `/region` | 省 / 市 / 区三级查询 |
| `index.py` | `/chat` | 向量索引重建 / 异步同步 / 索引统计 |
| `files.py` | `/files` | 文件上传（头像 / 评价图片）/ 下载 |
| `health.py` | `/health` | 健康检查 / 数据库连接检测 |

### 数据库模型清单（20 个 Model）

| Model 类 | 表名 | 关键字段 |
|---|---|---|
| `Admin` | `admin` | username, password, name, avatar, role, must_change_password |
| `User` | `user` | username, password, name, avatar, role, **balance**(DECIMAL) |
| `Category` | `category` | name |
| `Goods` | `goods` | name, price, description, detail, ingredients, specs, shelf_life, weight, origin, serves, img, num, unit, FK→Category |
| `Address` | `address` | user(FK), name, phone, province/city/town(FK), detail, is_default |
| `Province/City/Town` | `tb_province/city/town` | 三级行政区划 |
| `Orders` | `orders` | order_no(UNIQUE), num, user(FK), goods(FK), address(FK), time, status, total_price |
| `WalletTransaction` | `wallet_transaction` | user(FK), type, amount, balance_after, request_id(UNIQUE) |
| `Review` | `review` | goods(FK), user(FK), order(FK, UNIQUE), rating(1-5), content, images(JSON), reply |
| `Notice` | `notice` | name, content, time |
| `Conversation` | `conversation` | user_id, owner_role, title |
| `Message` | `message` | conversation(FK), role, content, prompt_tokens, completion_tokens, latency_ms, model |
| `Favorite` | `favorite` | user(FK), goods(FK), UNIQUE(user, goods) |
| `Knowledge` | `knowledge` | filename, original_name, file_size, chunk_count |
| `IndexTask` | `index_task` | entity_type, entity_id, action, status, attempts |
| `OpsReport` | `ops_report` | days, summary(LLM), facts(JSON), model |
| `AuditLog` | `audit_log` | operator_role, operator_id, action, target_type, target_id, detail(JSON), ip |
| `Notification` | `notification` | user_id, owner_role, type, title, content, is_read |

---

## 二、功能差距分析（vs 成熟商城系统）

### A. 高优先级缺口（直接影响交易闭环）

| # | 功能 | 当前现状 | 成熟系统标准 | 上线影响 |
|---|---|---|---|---|
| 1 | **真实支付** | 仅模拟充值（余额体系） | 微信 / 支付宝扫码支付 | 无法上线运营 |
| 2 | **库存管理** | `goods.num` 单字段，下单减库存，取消恢复 | 库存变动日志 / 安全库存预警 / 批量盘点 | 运营风险高 |
| 3 | **订单售后** | 仅取消（含退款回滚），无退货退款流程 | 退款申请 / 退货物流 / 售后工单 | 用户投诉无门 |
| 4 | **物流对接** | 管理员手动标记"已发货"，无物流单号 | 快递100 / 菜鸟 API 实时追踪 | 用户体验差 |
| 5 | **商品上下架** | 无状态字段，删除即下架 | `is_active` 草稿 / 上架 / 下架三态 | 运营不便 |

### B. 中优先级缺口（影响用户体验与运营效率）

| # | 功能 | 当前现状 | 成熟系统标准 |
|---|---|---|---|
| 6 | **购物车** | 无，直接"立即预订" | 加购 / 合并下单 / 价格快照 |
| 7 | **优惠券 / 促销** | 无 | 满减券 / 折扣券 / 限时活动 |
| 8 | **订单详情页** | 仅列表，无独立详情页 | 完整订单详情 + 物流时间轴 |
| 9 | **订单支付超时** | 无超时机制 | 30 分钟未支付自动取消 |
| 10 | **审计日志前端** | 仅后端写入 | 管理员可查看操作审计记录 |
| 11 | **数据导出** | 无 | 订单 / 商品 / 用户 CSV/Excel 导出 |
| 12 | **商品多图** | 商品仅单张主图 | 多图轮播 + 缩略图列表 |

### C. 低优先级缺口（锦上添花）

| # | 功能 | 说明 |
|---|---|---|
| 13 | 商品标签 / 属性 | 如"新品""爆款""低糖"标签体系 |
| 14 | 用户等级 / 积分 | 消费积分、等级权益 |
| 15 | 分销 / 推荐码 | 邀请注册返佣 |
| 16 | 多语言 / 国际化 | i18n 支持 |
| 17 | 移动端适配 | 当前仅有响应式，未做独立移动端 |

---

## 三、AI 功能深化规划

### 现有 AI 能力盘点

#### Agent 1：客服 Agent

配置文件：`agents/config/customer_service.json`

| 工具 | 实现文件 | 功能 |
|---|---|---|
| `search_knowledge` | `tools/knowledge.py` | 检索 ChromaDB 知识库（店铺政策、商品语义索引） |
| `get_order_status` | `tools/order/repository.py` | 查询当前用户的订单详情或最近订单列表 |
| `cancel_order` | `tools/order/repository.py` | 事务内取消订单并恢复库存，含意图安全校验 |
| `recommend_cake` | `tools/product/search.py` | 个性化蛋糕推荐（文本相关性 + 用户画像打分） |
| `check_stock` | `tools/product/search.py` | 按名称关键词查询实时库存 |
| `get_current_time` | `tools/business.py` | 返回门店时区当前时间 |

**基础设施**：
- **Grounding**：调用模型前注入 MySQL 商品事实，防止幻觉
- **Grounding 校验**：回答后用 `rebuild_product_answer` 确保商品信息来自 MySQL
- **RAG**：ChromaDB 向量检索 + 异步索引同步

#### Agent 2：运营分析 Agent

配置文件：`agents/config/ops_assistant.json`

| 工具 | 实现文件 | 功能 |
|---|---|---|
| `analyze_product_reviews` | `ops/analysis.py` | 星级分布、好评率、高频关键词、差评聚焦分析 |
| `analyze_product_sales` | `ops/analysis.py` | 指定商品日销趋势 / 全店热销滞销排行 |
| `analyze_inventory_status` | `ops/analysis.py` | 库存水位分布、资金占用、补货预警 |
| `analyze_product_performance` | `ops/analysis.py` | 销量 + 评价 + 库存加权综合评分（A/B/C/D） |

### 可拓展的 AI 功能

| # | 功能 | 实现路径 | 业务价值 |
|---|---|---|---|
| A1 | **商品详情 AI 问答** | 前端组件已预留（`GoodsAIQa.vue`），后端对接客服 Agent 的知识库检索工具 | 商品页转化率提升 |
| A2 | **智能推荐引擎** | 当前仅规则 + 语义双路，可加入协同过滤（用户行为矩阵） | 首页 / 详情页个性化 |
| A3 | **AI 生成商品描述** | 管理员输入关键词 → LLM 生成详情 / 卖点文案 | 运营效率提升 |
| A4 | **评价情感分析** | 已有 `analyze_product_reviews`，可扩展为自动标签（口感 / 配送 / 包装） | 差评预警 |
| A5 | **智能定价建议** | 基于销量趋势 + 竞品数据 + 成本的动态定价建议 | 利润优化 |
| A6 | **AI 客服意图识别增强** | 当前取消订单有意图校验，可扩展到退换货 / 投诉 / 咨询分类 | 客服效率提升 |
| A7 | **图片识别验货** | 上传蛋糕照片 → 视觉模型判断品相（与评价图片关联） | 品控溯源 |

---

## 四、新增功能实施规划

### Phase 1：交易闭环（上线前必须）

| 序号 | 功能 | 后端改动 | 前端改动 | 预估工作量 |
|---|---|---|---|---|
| 1.1 | **真实支付** | 接入支付 SDK，订单状态增加"待支付→已支付"，支付回调 | 收银台页面 / 支付结果页 | 3-5 天 |
| 1.2 | **库存管理增强** | 库存变动日志表，安全库存阈值，补货预警接口 | 库存管理页面 | 2-3 天 |
| 1.3 | **商品上下架状态** | `goods` 表加 `is_active` 字段，筛选条件更新 | 商品列表增加状态切换 | 1 天 |
| 1.4 | **订单详情页** | 订单详情 + 物流信息接口 | 独立订单详情页（含物流时间轴） | 2 天 |
| 1.5 | **订单支付超时** | 定时任务扫描超时订单自动取消 | 倒计时提示 | 1 天 |

**Phase 1 合计预估：9-12 天**

### Phase 2：体验优化（上线后迭代）

| 序号 | 功能 | 说明 | 预估工作量 |
|---|---|---|---|
| 2.1 | **购物车** | 前端状态管理 + 后端购物车表 | 3 天 |
| 2.2 | **商品多图** | `goods` 表改 `img` 为 JSON 数组，前端轮播 | 2 天 |
| 2.3 | **订单售后** | 退款申请表 + 退货流程 + 管理员审核 | 3 天 |
| 2.4 | **物流对接** | 快递100 API 集成 | 2 天 |
| 2.5 | **优惠券系统** | 优惠券表 + 发放表 + 下单抵扣逻辑 | 3-4 天 |
| 2.6 | **审计日志前端** | 管理员查看操作日志页面 | 1 天 |
| 2.7 | **数据导出** | 后端 CSV 生成 + 前端下载触发 | 1 天 |

**Phase 2 合计预估：15-16 天**

### Phase 3：AI 深化

| 序号 | 功能 | 说明 | 预估工作量 |
|---|---|---|---|
| 3.1 | **商品页 AI 问答** | 后端接入客服 Agent 知识库工具 | 2 天 |
| 3.2 | **AI 生成商品描述** | 新增 Agent 工具 + 管理端 UI | 2 天 |
| 3.3 | **智能推荐增强** | 协同过滤 + 用户行为埋点 | 3-4 天 |
| 3.4 | **评价情感标签** | 扩展现有 review 分析为自动标签 | 2 天 |

**Phase 3 合计预估：9-10 天**

---

## 五、架构建议

### 1. 支付架构

- 抽象支付网关接口（`PaymentGateway`），支持微信 / 支付宝 / 余额三种实现
- 支付回调走幂等校验（`request_id` 唯一键已有）
- 余额支付已有完整事务链路，可复用

### 2. 库存架构

- 引入 `stock_log` 表记录每次变动（下单扣减、取消恢复、管理员调整）
- 当前 `goods.num` 直接更新改为原子操作（`UPDATE goods SET num = num - ? WHERE num >= ?`）
- 安全库存阈值与 AI 运营 Agent 的补货预警联动

### 3. 订单状态机

- **当前**：待发货 → 已发货 → 待评价 → 已评价 / 已取消
- **扩展**：待支付 → 已支付 → 待发货 → 已发货 → 已签收 → 待评价 → 已评价 / 退款中 → 已退款
- 状态机已由 `domain/order_status.py` 管理，扩展影响可控

### 4. AI 扩展建议

- **商品页 AI 问答后端**：复用客服 Agent 的 `search_knowledge` + `check_stock` 工具，新增 `POST /qa/goods` 端点
- **推荐系统**：当前双路（规则 + 语义）架构可扩展，增加用户行为事件表（浏览 / 收藏 / 下单）驱动协同过滤
- **Agent 工具注册**：现有 `factory.py` + JSON 配置的模式已支持热插拔，新增工具无需改框架

---

## 六、结论

当前系统**已完成 MVP 核心闭环**（商品浏览 → 下单 → 评价 → 客服），AI 能力显著（双 Agent + RAG + Grounding）。

**最紧迫的上线阻断项**：
1. **真实支付**（#1.1）— 无法上线运营的硬性前提
2. **库存管理增强**（#1.2）— 运营风险控制
3. **订单详情页**（#1.4）— 用户体验基线

**建议按 Phase 1 → 2 → 3 分期迭代**，Phase 1 预计 2 周可完成上线准备，总工期约 5-6 周可达到可运营状态。
