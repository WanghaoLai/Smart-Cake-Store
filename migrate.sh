#!/usr/bin/env bash
# ============================================================
# 数据库迁移幂等执行器
# ------------------------------------------------------------
# 工作流：
#   1. 从 fastapi-app/.env 读取 DB 连接信息
#   2. 创建 _schema_migrations 跟踪表
#   3. 若 orders 表不存在 → 先导入 cake_store.sql（基础 schema）
#   4. 按文件名升序执行 migrations/*.sql，已应用的自动跳过
#   5. 全程强制 --default-character-set=utf8mb4
#
# 用法：
#   ./migrate.sh                # 默认读 fastapi-app/.env
#   DB_PASSWORD=xxx ./migrate.sh  # 也可走环境变量覆盖
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/fastapi-app/.env"
BASE_SQL="${SCRIPT_DIR}/cake_store.sql"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"

# ---- 加载 .env（不覆盖已存在的环境变量）----
if [[ -f "$ENV_FILE" ]]; then
  # 标准的 KEY=value 文件可直接 source；set -a 让所有赋值自动 export
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-cake_store}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "❌ DB_PASSWORD 未配置：请在 fastapi-app/.env 中设置，或通过环境变量 DB_PASSWORD 提供" >&2
  exit 1
fi

MYSQL_BIN="${MYSQL_BIN:-mysql}"
if ! command -v "$MYSQL_BIN" >/dev/null 2>&1; then
  echo "❌ 找不到 mysql 客户端。macOS 默认路径 /usr/local/mysql/bin/mysql，可通过 MYSQL_BIN 环境变量指定" >&2
  exit 1
fi

# 统一的连接参数：强制 utf8mb4 客户端字符集，杜绝中文乱码
MYSQL_ARGS=(-h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" \
            --default-character-set=utf8mb4 "$DB_NAME")

# 工具函数：执行 mysql 命令，吞掉 password 警告但不污染退出码
# grep -v 在所有行被过滤时会返回 1，会触发 set -o pipefail 误报失败，
# 所以先抓 mysql 真实退出码，再做过滤展示
run_mysql() {
  local output exit_code
  output=$("$MYSQL_BIN" "${MYSQL_ARGS[@]}" "$@" 2>&1)
  exit_code=$?
  if [[ -n "$output" ]]; then
    echo "$output" | grep -v "Using a password" || true
  fi
  return "$exit_code"
}

# ---- 1. 创建跟踪表（幂等）----
echo "▶ 初始化 _schema_migrations 跟踪表..."
run_mysql <<'SQL' || true
CREATE TABLE IF NOT EXISTS `_schema_migrations` (
  `filename` varchar(255) NOT NULL,
  `applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`filename`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='迁移执行记录';
SQL

# ---- 2. 基础 schema 检测 ----
echo "▶ 检测 orders 表是否已初始化..."
ORDERS_EXISTS=$(run_mysql -N -B -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME' AND table_name='orders';" || true)

if [[ "$ORDERS_EXISTS" -eq 0 ]]; then
  if [[ ! -f "$BASE_SQL" ]]; then
    echo "❌ orders 表不存在，且找不到基础 dump $BASE_SQL" >&2
    exit 1
  fi
  echo "▶ 导入基础 schema: $BASE_SQL"
  run_mysql < "$BASE_SQL" || true
  # 把基础 schema 标记为已应用（防止下次重复执行；cake_store.sql 含 DROP TABLE，重跑会清空数据）
  run_mysql -e \
    "INSERT IGNORE INTO _schema_migrations (filename) VALUES ('__cake_store.sql');" || true
else
  echo "✓ orders 表已存在，跳过基础 schema"
fi

# ---- 3. 顺序执行未应用的迁移 ----
shopt -s nullglob
# 兼容 macOS 自带 bash 3.2（无 mapfile）：用 while-read 读入数组
MIGRATION_FILES=()
while IFS= read -r line; do
  MIGRATION_FILES+=("$line")
done < <(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)

if [[ ${#MIGRATION_FILES[@]} -eq 0 ]]; then
  echo "ℹ️  migrations/ 下没有迁移文件需要执行"
  exit 0
fi

APPLIED=0
SKIPPED=0
for f in "${MIGRATION_FILES[@]}"; do
  name="$(basename "$f")"
  IS_APPLIED=$(run_mysql -N -B -e \
    "SELECT COUNT(*) FROM _schema_migrations WHERE filename='$name';" || true)

  if [[ "$IS_APPLIED" -gt 0 ]]; then
    echo "✓ 已应用，跳过: $name"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  echo "▶ 执行: $name"
  if run_mysql < "$f"; then
    run_mysql -e \
      "INSERT INTO _schema_migrations (filename) VALUES ('$name');" || true
    APPLIED=$((APPLIED + 1))
  else
    echo "❌ 执行失败: $name" >&2
    exit 1
  fi
done

echo ""
echo "✅ 完成：本次应用 $APPLIED 个，跳过 $SKIPPED 个已应用的迁移"
