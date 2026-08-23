#!/usr/bin/env bash
# ============================================================
# 数据库迁移幂等执行器
# ------------------------------------------------------------
# 位置：db/（数据库相关文件的唯一入口）
# 工作流：
#   1. 读取 fastapi-app/.env 连接信息（命令行环境变量优先于 .env）
#   2. 目标库不存在时自动创建（utf8mb4）
#   3. 创建 _schema_migrations 跟踪表
#   4. 若 orders 表不存在 → 导入 cake_store.sql（基础 schema，
#      已预标记 001–011 为已应用）→ 导入 seed_base.sql（演示账号/
#      区划/分类/公告，INSERT IGNORE 幂等）
#   5. 按文件名升序执行 migrations/*.sql，已应用的自动跳过
#   6. 全程强制 --default-character-set=utf8mb4
#
# 用法（在项目根目录执行）：
#   ./db/migrate.sh                          # 默认读 fastapi-app/.env
#   DB_NAME=cake_store_test ./db/migrate.sh   # 环境变量临时覆盖目标库
#   DB_PASSWORD=xxx ./db/migrate.sh           # 同理覆盖密码等连接参数
#
# 文件说明见同目录 README.md。
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/fastapi-app/.env"
BASE_SQL="${SCRIPT_DIR}/cake_store.sql"
SEED_SQL="${SCRIPT_DIR}/seed_base.sql"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"

# ---- 记录调用方显式传入的环境变量（source .env 后恢复，保证覆盖生效）----
_OVERRIDE_KEYS=(DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD MYSQL_BIN)
_OVERRIDE_VALUES=()
for _key in "${_OVERRIDE_KEYS[@]}"; do
  _OVERRIDE_VALUES+=("${!_key:-}")
done

# ---- 加载 .env（标准 KEY=value 文件）----
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# 恢复命令行覆盖值，导出供后续使用
_index=0
for _key in "${_OVERRIDE_KEYS[@]}"; do
  _value="${_OVERRIDE_VALUES[$_index]}"
  if [[ -n "$_value" ]]; then
    export "$_key=$_value"
  fi
  _index=$((_index + 1))
done

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-cake_store}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "❌ DB_PASSWORD 未配置：请在 fastapi-app/.env 中设置，或通过环境变量 DB_PASSWORD 提供" >&2
  exit 1
fi

# 库名同时用于 SQL 查询与标识符；先收紧为 MySQL 安全标识符子集，
# 避免配置错误变成意外的多语句执行。
if [[ ! "$DB_NAME" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "❌ DB_NAME 只能包含字母、数字和下划线" >&2
  exit 1
fi

MYSQL_BIN="${MYSQL_BIN:-mysql}"
if ! command -v "$MYSQL_BIN" >/dev/null 2>&1; then
  echo "❌ 找不到 mysql 客户端。macOS 默认路径 /usr/local/mysql/bin/mysql，可通过 MYSQL_BIN 环境变量指定" >&2
  exit 1
fi

# 密码不放进命令行，避免被同机器的进程列表读取。
export MYSQL_PWD="$DB_PASSWORD"

# 不带库名的连接参数（用于建库检测与创建）
CONN_ARGS=(-h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" \
           --default-character-set=utf8mb4)

# 统一的连接参数（带库名）：强制 utf8mb4 客户端字符集，杜绝中文乱码
MYSQL_ARGS=("${CONN_ARGS[@]}" "$DB_NAME")

# 工具函数：执行 mysql 命令，吞掉 password 警告但不污染退出码
# grep -v 在所有行被过滤时会返回 1，会触发 set -o pipefail 误报失败，
# 所以先抓 mysql 真实退出码，再做过滤展示
run_mysql() {
  local output exit_code
  # 放在 if 条件中可避免 set -e 在我们打印 MySQL 错误前提前退出。
  if output=$("$MYSQL_BIN" "${MYSQL_ARGS[@]}" "$@" 2>&1); then
    exit_code=0
  else
    exit_code=$?
  fi
  if [[ -n "$output" ]]; then
    echo "$output" | grep -v "Using a password" || true
  fi
  return "$exit_code"
}

# ---- 0. 目标库不存在时自动创建（全新机器一条命令可用）----
DB_EXISTS=$("$MYSQL_BIN" "${CONN_ARGS[@]}" -N -B -e \
  "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='$DB_NAME';" 2>/dev/null)
if [[ "$DB_EXISTS" != "1" ]]; then
  echo "▶ 目标库 $DB_NAME 不存在，自动创建（utf8mb4）..."
  "$MYSQL_BIN" "${CONN_ARGS[@]}" -e \
    "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
fi

# ---- 1. 创建跟踪表（幂等）----
echo "▶ 初始化 _schema_migrations 跟踪表..."
run_mysql <<'SQL'
CREATE TABLE IF NOT EXISTS `_schema_migrations` (
  `filename` varchar(255) NOT NULL,
  `applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`filename`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='迁移执行记录';
SQL

# ---- 2. 基础 schema 检测 ----
echo "▶ 检测 orders 表是否已初始化..."
ORDERS_EXISTS=$(run_mysql -N -B -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME' AND table_name='orders';")

if [[ "$ORDERS_EXISTS" -eq 0 ]]; then
  if [[ ! -f "$BASE_SQL" ]]; then
    echo "❌ orders 表不存在，且找不到基础 schema $BASE_SQL" >&2
    exit 1
  fi
  echo "▶ 导入基础 schema: $BASE_SQL"
  run_mysql < "$BASE_SQL"
  # 把基础 schema 标记为已应用（防止下次重复执行；cake_store.sql 含 DROP TABLE，重跑会清空数据）
  run_mysql -e \
    "INSERT IGNORE INTO _schema_migrations (filename) VALUES ('__cake_store.sql');"
  # 基础种子：演示账号/区划/分类/公告。INSERT IGNORE 幂等，失败即中止（缺失会导致无法登录）
  if [[ -f "$SEED_SQL" ]]; then
    echo "▶ 导入基础种子: $SEED_SQL"
    run_mysql < "$SEED_SQL"
  else
    echo "⚠️  未找到 $SEED_SQL，跳过基础种子（新库将没有演示账号与区划数据）" >&2
  fi
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
    "SELECT COUNT(*) FROM _schema_migrations WHERE filename='$name';")

  if [[ "$IS_APPLIED" -gt 0 ]]; then
    echo "✓ 已应用，跳过: $name"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  echo "▶ 执行: $name"
  if run_mysql < "$f"; then
    run_mysql -e \
      "INSERT INTO _schema_migrations (filename) VALUES ('$name');"
    APPLIED=$((APPLIED + 1))
  else
    echo "❌ 执行失败: $name" >&2
    exit 1
  fi
done

echo ""
echo "✅ 完成：本次应用 $APPLIED 个，跳过 $SKIPPED 个已应用的迁移（目标库：${DB_NAME}）"
