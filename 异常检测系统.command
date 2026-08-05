#!/usr/bin/env bash

# 异常检测系统 - 前后端一键启动脚本
#
# 使用方法：
#   1. macOS：在 Finder 中双击“异常检测系统.command”。
#   2. 终端：在任意目录执行 /path/to/异常检测系统.command。
#   3. 停止：在脚本窗口按 Ctrl+C，将同时停止本脚本启动的前后端。
#
# 可选环境变量：
#   BACKEND_PORT=9090 FRONTEND_PORT=5173 ./异常检测系统.command
#   OPEN_BROWSER=0 ./异常检测系统.command  # 调试时不打开浏览器

set -u

# 无论从哪里启动，都自动进入脚本所在的项目根目录。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

BACKEND_DIR="$SCRIPT_DIR/fastapi-app"
FRONTEND_DIR="$SCRIPT_DIR/vue"
BACKEND_START_PORT="${BACKEND_PORT:-9090}"
FRONTEND_START_PORT="${FRONTEND_PORT:-5173}"
FRONTEND_REQUESTED_PORT="$FRONTEND_START_PORT"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
BACKEND_PID=""
FRONTEND_PID=""
LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/anomaly-system.XXXXXX")"

print_error() {
  printf '\033[31m%s\033[0m\n' "$1" >&2
}

pause_on_error() {
  print_error "$1"
  printf '\n按回车键关闭窗口...'
  read -r _ </dev/tty 2>/dev/null || true
  exit 1
}

is_valid_port() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -ge 1 ] && [ "$1" -le 65535 ]
}

is_port_free() {
  "$PYTHON_BIN" - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
}

find_free_port() {
  local port="$1"
  local attempts=0
  while [ "$port" -le 65535 ] && [ "$attempts" -lt 200 ]; do
    if is_port_free "$port"; then
      printf '%s\n' "$port"
      return 0
    fi
    port=$((port + 1))
    attempts=$((attempts + 1))
  done
  return 1
}

stop_process_tree() {
  local pid="$1"
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || return 0
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
}

cleanup() {
  trap - EXIT INT TERM
  printf '\n正在停止前后端服务...\n'
  stop_process_tree "$FRONTEND_PID"
  stop_process_tree "$BACKEND_PID"
  wait "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  printf '服务已停止。本次日志：%s\n' "$LOG_DIR"
}
trap cleanup EXIT INT TERM

if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
elif [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
  PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 2>/dev/null || true)"
fi

[ -n "$PYTHON_BIN" ] || pause_on_error "未找到 Python 3，请先安装 Python 3。"
command -v npm >/dev/null 2>&1 || pause_on_error "未找到 npm，请先安装 Node.js。"
[ -d "$BACKEND_DIR" ] || pause_on_error "未找到后端目录：$BACKEND_DIR"
[ -f "$FRONTEND_DIR/package.json" ] || pause_on_error "未找到前端项目：$FRONTEND_DIR"
[ -d "$FRONTEND_DIR/node_modules" ] || pause_on_error "前端依赖未安装，请先在 vue 目录执行 npm install。"
"$PYTHON_BIN" -c 'import fastapi, uvicorn, tortoise' >/dev/null 2>&1 || \
  pause_on_error "后端依赖不完整，请先执行：$PYTHON_BIN -m pip install -r fastapi-app/requirements.txt"

is_valid_port "$BACKEND_START_PORT" || pause_on_error "BACKEND_PORT 必须是 1-65535 之间的整数。"
is_valid_port "$FRONTEND_START_PORT" || pause_on_error "FRONTEND_PORT 必须是 1-65535 之间的整数。"

BACKEND_PORT="$(find_free_port "$BACKEND_START_PORT")" || pause_on_error "找不到可用的后端端口。"
if [ "$BACKEND_PORT" != "$BACKEND_START_PORT" ]; then
  printf '后端端口 %s 已被占用，自动切换到 %s。\n' "$BACKEND_START_PORT" "$BACKEND_PORT"
fi


# 避免前端和后端被分配到同一端口。
if [ "$FRONTEND_START_PORT" = "$BACKEND_PORT" ]; then
  FRONTEND_START_PORT=$((FRONTEND_START_PORT + 1))
fi
FRONTEND_PORT="$(find_free_port "$FRONTEND_START_PORT")" || pause_on_error "找不到可用的前端端口。"
if [ "$FRONTEND_PORT" != "$FRONTEND_REQUESTED_PORT" ]; then
  printf '前端端口 %s 不可用，自动切换到 %s。\n' "$FRONTEND_REQUESTED_PORT" "$FRONTEND_PORT"
fi

BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
FRONTEND_URL="http://127.0.0.1:$FRONTEND_PORT"

printf '\n正在启动后端：%s\n' "$BACKEND_URL"
(
  cd "$BACKEND_DIR" || exit 1
  exec "$PYTHON_BIN" -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT"
) >"$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

printf '正在启动前端：%s\n' "$FRONTEND_URL"
(
  cd "$FRONTEND_DIR" || exit 1
  export VITE_BASE_URL="$BACKEND_URL"
  # 强制 Vite 重新优化依赖，避免上次开发会话的旧模块缓存残留。
  exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort --force
) >"$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

wait_for_service() {
  local name="$1"
  local url="$2"
  local pid="$3"
  local log_file="$4"
  local count=0
  while [ "$count" -lt 60 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      print_error "$name 启动失败，日志如下："
      tail -n 40 "$log_file" >&2
      return 1
    fi
    if curl --silent --fail --max-time 2 "$url" >/dev/null 2>&1; then
      printf '%s 已就绪。\n' "$name"
      return 0
    fi
    sleep 1
    count=$((count + 1))
  done
  print_error "等待 $name 超时，日志如下："
  tail -n 40 "$log_file" >&2
  return 1
}

wait_for_service "后端" "$BACKEND_URL/" "$BACKEND_PID" "$LOG_DIR/backend.log" || exit 1
wait_for_service "前端" "$FRONTEND_URL/" "$FRONTEND_PID" "$LOG_DIR/frontend.log" || exit 1

printf '\n所有服务已启动！\n'
printf '  前端：%s\n  后端：%s\n  日志：%s\n' "$FRONTEND_URL" "$BACKEND_URL" "$LOG_DIR"

if [ "$OPEN_BROWSER" != "0" ]; then
  # 启动参数让浏览器进行一次新导航，不复用旧 Vite 页面的 HMR 状态。
  BROWSER_URL="$FRONTEND_URL/?startup=$(date +%s)"
  if command -v open >/dev/null 2>&1; then
    open "$BROWSER_URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$BROWSER_URL" >/dev/null 2>&1 &
  else
    printf '未找到可用的浏览器打开命令，请手动访问：%s\n' "$FRONTEND_URL"
  fi
fi

printf '\n按 Ctrl+C 停止所有服务。\n'
wait "$BACKEND_PID" "$FRONTEND_PID"
