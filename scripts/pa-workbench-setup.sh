#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PA_DIR="$ROOT_DIR/pa-ai-workbench"
PA_BACKEND_DIR="$PA_DIR/backend"
PA_FRONTEND_DIR="$PA_DIR/frontend"

INSTALL_DEPS=1
for arg in "$@"; do
  case "$arg" in
    --skip-install)
      INSTALL_DEPS=0
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/pa-workbench-setup.sh [--skip-install]

Prepare a local PA + WeKnora workbench checkout.

The script creates local env files from examples and optionally installs PA
backend/frontend dependencies. It never prints or writes secret values.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

log() {
  printf '[pa-setup] %s\n' "$1"
}

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ -f "$dst" ]]; then
    log "exists: ${dst#$ROOT_DIR/}"
    return
  fi
  if [[ ! -f "$src" ]]; then
    echo "Missing template: $src" >&2
    exit 1
  fi
  cp "$src" "$dst"
  log "created: ${dst#$ROOT_DIR/}"
}

command_required() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command: $name" >&2
    exit 1
  fi
}

copy_if_missing "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
copy_if_missing "$PA_BACKEND_DIR/.env.example" "$PA_BACKEND_DIR/.env"
copy_if_missing "$PA_FRONTEND_DIR/.env.example" "$PA_FRONTEND_DIR/.env.local"

if [[ "$INSTALL_DEPS" -eq 0 ]]; then
  log "dependency install skipped"
  log "next: scripts/pa-workbench-start.sh"
  exit 0
fi

if [[ ! -x "$PA_BACKEND_DIR/.venv/bin/python" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CREATE_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_CREATE_BIN="$(command -v python)"
  else
    echo "Missing Python. Install Python 3.11+ or create $PA_BACKEND_DIR/.venv manually." >&2
    exit 1
  fi
  log "creating backend venv"
  "$PYTHON_CREATE_BIN" -m venv "$PA_BACKEND_DIR/.venv"
fi

log "installing backend dependencies"
"$PA_BACKEND_DIR/.venv/bin/python" -m pip install -r "$PA_BACKEND_DIR/requirements.txt"

command_required npm
if [[ ! -d "$PA_FRONTEND_DIR/node_modules" ]]; then
  log "installing frontend dependencies"
  (
    cd "$PA_FRONTEND_DIR"
    if [[ -f package-lock.json ]]; then
      npm ci
    else
      npm install
    fi
  )
else
  log "exists: pa-ai-workbench/frontend/node_modules"
fi

log "setup complete"
log "edit local env files as needed; do not commit them"
log "next: scripts/pa-workbench-start.sh"
