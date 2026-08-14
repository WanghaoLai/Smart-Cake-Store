# 数据库迁移

## 文件结构

```
.
├── ../cake_store.sql         # 基础 schema + 初始数据（全量 dump，含 address_region / goods_detail 字段）
├── 001_order_status.sql      # 给 orders 增加 status 列
├── 002_review.sql            # 创建 review 表
├── 003_conversation_owner_identity.sql # 会话按角色 + ID 隔离用户与管理员
└── archive/                  # 已废弃迁移：cake_store.sql 最新 dump 已包含其变更
    ├── migration_address_region.sql
    └── migration_goods_detail.sql
```

## 执行方式

**推荐**：用项目根目录的幂等执行器

```bash
./migrate.sh
```

执行器会：
1. 自动从 `fastapi-app/.env` 读取数据库连接信息
2. 创建 `_schema_migrations` 跟踪表
3. 检测 `orders` 表是否存在；不存在则先导入 `cake_store.sql`
4. 按文件名升序逐个执行 `migrations/*.sql`（不扫 `archive/`）
5. 全程强制 `--default-character-set=utf8mb4`，杜绝中文乱码
6. 已应用的迁移自动跳过，可安全重跑

**手动**：仅推荐在执行器失败时排查使用

```bash
mysql -uroot -p<password> --default-character-set=utf8mb4 cake_store < migrations/001_order_status.sql
```

注意：必须加 `--default-character-set=utf8mb4`，否则 mysql CLI 默认 latin1 会让中文常量双重编码。

## 新增迁移

1. 文件名格式：`NNN_<动词>_<对象>.sql`，例如 `003_add_user_avatar_field.sql`
2. 文件开头必须包含 `SET NAMES utf8mb4;`（防止字符集陷阱）
3. 不需要写幂等保护（执行器通过 `_schema_migrations` 表跳过已应用的）
4. 不要修改已发布过的迁移文件，新需求开新文件
