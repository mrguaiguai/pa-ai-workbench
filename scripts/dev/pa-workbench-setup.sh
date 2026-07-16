#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLATFORM_ROOT="$REPOSITORY_ROOT/platform/weknora"
PA_BACKEND_DIR="$REPOSITORY_ROOT/apps/pa-api"
PA_FRONTEND_DIR="$REPOSITORY_ROOT/apps/pa-web"
LEGACY_PA_RUNTIME_ROOT="$REPOSITORY_ROOT/pa-ai-workbench"
LEGACY_BACKEND_RUNTIME_DIR="$LEGACY_PA_RUNTIME_ROOT/backend"
CANONICAL_BACKEND_RUNTIME_DIR="$REPOSITORY_ROOT/.local/pa-api"

legacy_backend_runtime_present() {
  [[ -f "$LEGACY_BACKEND_RUNTIME_DIR/.env" \
    || -d "$LEGACY_BACKEND_RUNTIME_DIR/.venv" \
    || -d "$LEGACY_BACKEND_RUNTIME_DIR/data" \
    || -d "$LEGACY_BACKEND_RUNTIME_DIR/uploads" ]]
}

if legacy_backend_runtime_present; then
  PA_BACKEND_RUNTIME_DIR="$LEGACY_BACKEND_RUNTIME_DIR"
else
  PA_BACKEND_RUNTIME_DIR="$CANONICAL_BACKEND_RUNTIME_DIR"
fi

INSTALL_DEPS=1
for arg in "$@"; do
  case "$arg" in
    --skip-install)
      INSTALL_DEPS=0
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/dev/pa-workbench-setup.sh [--skip-install]

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
    log "exists: ${dst#$PLATFORM_ROOT/}"
    return
  fi
  if [[ ! -f "$src" ]]; then
    echo "Missing template: $src" >&2
    exit 1
  fi
  cp "$src" "$dst"
  log "created: ${dst#$PLATFORM_ROOT/}"
}

command_required() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command: $name" >&2
    exit 1
  fi
}

mkdir -p "$PA_BACKEND_RUNTIME_DIR"
copy_if_missing "$PLATFORM_ROOT/.env.example" "$REPOSITORY_ROOT/.env"
copy_if_missing "$PLATFORM_ROOT/.env.example" "$PLATFORM_ROOT/.env"
copy_if_missing "$PA_BACKEND_DIR/.env.example" "$PA_BACKEND_RUNTIME_DIR/.env"
copy_if_missing "$PA_FRONTEND_DIR/.env.example" "$PA_FRONTEND_DIR/.env.local"

if [[ "$INSTALL_DEPS" -eq 0 ]]; then
  log "dependency install skipped"
  log "next: scripts/dev/pa-workbench-start.sh"
  exit 0
fi

if [[ -x "$PA_BACKEND_DIR/.venv/bin/python" ]]; then
  PA_PYTHON_BIN="$PA_BACKEND_DIR/.venv/bin/python"
elif [[ -x "$PA_BACKEND_RUNTIME_DIR/.venv/bin/python" ]]; then
  PA_PYTHON_BIN="$PA_BACKEND_RUNTIME_DIR/.venv/bin/python"
else
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
  PA_PYTHON_BIN="$PA_BACKEND_DIR/.venv/bin/python"
fi

log "installing backend dependencies"
"$PA_PYTHON_BIN" -m pip install -r "$PA_BACKEND_DIR/requirements.txt"

if [[ ! -d "$PA_FRONTEND_DIR/node_modules" ]]; then
  log "installing frontend dependencies"
  (
    cd "$PA_FRONTEND_DIR"
    if command -v npm >/dev/null 2>&1 && [[ -f package-lock.json ]]; then
      npm ci
    elif command -v npm >/dev/null 2>&1; then
      npm install
    elif command -v pnpm >/dev/null 2>&1; then
      # A lockfile-free pnpm fallback keeps the checkout clean on hosts where
      # Node is provisioned with pnpm but npm is not installed.
      pnpm install --lockfile=false
    else
      echo "Missing npm or pnpm. Install a Node package manager." >&2
      exit 1
    fi
  )
else
  log "exists: apps/pa-web/node_modules"
fi

log "setup complete"
log "edit local env files as needed; do not commit them"
log "next: scripts/dev/pa-workbench-start.sh"
