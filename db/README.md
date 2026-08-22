# 数据库目录（db/）

数据库相关文件的唯一入口。**给新库用 dump，给活库用增量迁移，历史进 archive——三样都提交 Git，只有运行时数据才进 `.gitignore`。**

## 目录结构与文件角色

```
db/
├── README.md                # 本文件
├── migrate.sh               # 幂等迁移执行器（唯一执行入口）
├── cake_store.sql           # 基础 schema（纯 DDL，2026-08-22 基线：已包含 001–009 全部
│                            #   结构变更，并在 _schema_migrations 中预标记为已应用）
├── seed_base.sql            # 全新部署基础种子：演示账号(bcrypt) + 省市区区划(3380 行)
│                            #   + 分类 + 公告；全部 INSERT IGNORE，幂等可重跑
└── migrations/
    ├── 001_order_status.sql             # orders 增加 status 列
    ├── 002_review.sql                   # 创建 review 表
    ├── 003_conversation_owner_identity.sql  # 会话按角色 + ID 隔离
    ├── 004_goods_price_decimal.sql      # 金额改为 DECIMAL(10,2)
    ├── 005_order_no_unique.sql          # 订单号去重 + 唯一索引
    ├── 006_orders_total_price.sql       # 订单价格快照列（含回填）
    ├── 007_file_url_relative.sql        # 存量上传 URL 清洗为相对路径
    ├── 008_message_usage.sql            # message 表 token 用量计量列
    ├── 009_ops_report.sql               # 运营报告表
    └── archive/             # 已合并进基础 dump 的历史迁移（不再执行，仅留档）
```

应用层数据脚本（Python，走 ORM，可重复执行）：

| 脚本 | 用途 |
|---|---|
| `fastapi-app/scripts/seed_goods.py` | 演示商品数据（含图片相对路径，分类对齐 seed_base） |
| `fastapi-app/scripts/seed_analysis_data.py` | 运营分析页演示数据（90 天订单/评价） |

## 使用

### 全新环境（一条命令）

```bash
# 在项目根目录执行；需已配置 fastapi-app/.env 的 DB_PASSWORD
./db/migrate.sh
```

执行器自动完成：建库（不存在时）→ 导入基础 schema（001–009 已预标记，不会重放）→ 导入基础种子（演示账号/区划/分类/公告）→ 执行未应用的增量迁移。

完成后即可用演示账号登录：管理员 `222/222`，用户 `234/234`。

### 存量环境升级

同样执行 `./db/migrate.sh`——检测到 `orders` 表已存在会跳过基础导入，只应用新增的增量迁移。**可安全重跑**：已应用的迁移自动跳过。

### 临时切换目标库（测试用）

```bash
DB_NAME=cake_store_test ./db/migrate.sh
```

命令行环境变量优先于 `.env`（`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `MYSQL_BIN` 同理）。

### 手动执行（仅排错用）

```bash
mysql -uroot -p<password> --default-character-set=utf8mb4 cake_store < db/migrations/001_order_status.sql
```

必须加 `--default-character-set=utf8mb4`，否则 mysql CLI 默认字符集会让中文常量双重编码。macOS 上 mysql 不在 PATH 时：`MYSQL_BIN=/usr/local/mysql/bin/mysql ./db/migrate.sh`。

## 新增迁移

1. 文件名格式：`NNN_<动词>_<对象>.sql`（编号递增，当前下一个是 `010`），例如 `010_add_user_avatar_field.sql`
2. 文件开头必须包含 `SET NAMES utf8mb4;`（防止字符集陷阱）
3. 不需要写幂等保护（执行器通过 `_schema_migrations` 表跳过已应用的）
4. 不要修改已发布过的迁移文件，新需求开新文件
5. 涉及表结构变更的后端代码必须与迁移文件在同一个提交中发布

## 基线合并流程（可选，嫌迁移文件多时）

当所有存量环境都已应用某批迁移后，可以把它们合并进基础 dump：

1. 从最新结构重新导出 `cake_store.sql`（**只导结构，不导业务数据**；真实数据严禁入库）
2. 在 dump 的 `_schema_migrations` Records 段预标记已合并的迁移文件名
3. 将对应文件移入 `migrations/archive/`
4. 同步更新本 README 的目录结构清单与根 README

## 数据安全红线

- `cake_store.sql` 含 `DROP TABLE`——对已有数据手工重跑会清库（执行器已内置防重入保护，勿绕过）
- 真实用户数据（地址、手机号、聊天记录、订单）**永远不进** Git；演示数据只放在 `seed_base.sql` 与应用层 seed 脚本中
