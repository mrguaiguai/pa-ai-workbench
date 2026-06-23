#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/tmp/dev-services"
LOG_DIR="$ROOT_DIR/logs/dev-services"

BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

PYTHON_BIN="${PYTHON_BIN:-$BACKEND_DIR/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"

mkdir -p "$RUNTIME_DIR" "$LOG_DIR"

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1
}

clear_stale_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]] && ! kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    rm -f "$pid_file"
  fi
}

port_owner() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR == 2 {print $1 " pid=" $2}'
}

start_backend() {
  clear_stale_pid "$BACKEND_PID_FILE"
  if is_running "$BACKEND_PID_FILE"; then
    echo "backend already running pid=$(cat "$BACKEND_PID_FILE")"
    return
  fi
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "backend python not found: $PYTHON_BIN" >&2
    exit 1
  fi
  local owner
  owner="$(port_owner "$BACKEND_PORT" || true)"
  if [[ -n "$owner" ]]; then
    echo "backend port $BACKEND_PORT is already in use by $owner"
    return
  fi
  (
    cd "$BACKEND_DIR"
    nohup "$PYTHON_BIN" -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
      >"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )
  echo "backend started pid=$(cat "$BACKEND_PID_FILE") log=$BACKEND_LOG"
}

start_frontend() {
  clear_stale_pid "$FRONTEND_PID_FILE"
  if is_running "$FRONTEND_PID_FILE"; then
    echo "frontend already running pid=$(cat "$FRONTEND_PID_FILE")"
    return
  fi
  if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
    echo "node not found. Set NODE_BIN or install node." >&2
    exit 1
  fi
  if [[ ! -f "$FRONTEND_DIR/node_modules/vite/bin/vite.js" ]]; then
    echo "vite not found under frontend/node_modules. Install frontend dependencies first." >&2
    exit 1
  fi
  local owner
  owner="$(port_owner "$FRONTEND_PORT" || true)"
  if [[ -n "$owner" ]]; then
    echo "frontend port $FRONTEND_PORT is already in use by $owner"
    return
  fi
  (
    cd "$FRONTEND_DIR"
    nohup "$NODE_BIN" node_modules/vite/bin/vite.js --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )
  echo "frontend started pid=$(cat "$FRONTEND_PID_FILE") log=$FRONTEND_LOG"
}

stop_one() {
  local name="$1"
  local pid_file="$2"
  if is_running "$pid_file"; then
    local pid
    pid="$(cat "$pid_file")"
    kill "$pid"
    rm -f "$pid_file"
    echo "$name stopped pid=$pid"
  else
    rm -f "$pid_file"
    echo "$name not running"
  fi
}

status_one() {
  local name="$1"
  local pid_file="$2"
  local port="$3"
  clear_stale_pid "$pid_file"
  if is_running "$pid_file"; then
    echo "$name running pid=$(cat "$pid_file") url=http://127.0.0.1:$port/"
  else
    local owner
    owner="$(port_owner "$port" || true)"
    if [[ -n "$owner" ]]; then
      echo "$name not managed, but port $port is in use by $owner"
    else
      echo "$name stopped"
    fi
  fi
}

case "${1:-status}" in
  start)
    start_backend
    start_frontend
    ;;
  stop)
    stop_one frontend "$FRONTEND_PID_FILE"
    stop_one backend "$BACKEND_PID_FILE"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    status_one backend "$BACKEND_PID_FILE" "$BACKEND_PORT"
    status_one frontend "$FRONTEND_PID_FILE" "$FRONTEND_PORT"
    ;;
  logs)
    echo "backend log:  $BACKEND_LOG"
    echo "frontend log: $FRONTEND_LOG"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}" >&2
    exit 2
    ;;
esac
