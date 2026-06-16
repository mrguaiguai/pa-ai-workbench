#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/logs/launchd"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
USER_DOMAIN="gui/$(id -u)"

BACKEND_LABEL="com.pa-ai-workbench.backend"
FRONTEND_LABEL="com.pa-ai-workbench.frontend"
BACKEND_PLIST="$LAUNCH_AGENT_DIR/$BACKEND_LABEL.plist"
FRONTEND_PLIST="$LAUNCH_AGENT_DIR/$FRONTEND_LABEL.plist"

PYTHON_BIN="${PYTHON_BIN:-$BACKEND_DIR/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node}"
if [[ ! -x "$NODE_BIN" ]]; then
  NODE_BIN="$(command -v node || true)"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "backend python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
  echo "node not found. Set NODE_BIN to an absolute node executable path." >&2
  exit 1
fi

if [[ ! -f "$FRONTEND_DIR/node_modules/vite/bin/vite.js" ]]; then
  echo "vite not found under frontend/node_modules. Install frontend dependencies first." >&2
  exit 1
fi

mkdir -p "$LAUNCH_AGENT_DIR" "$LOG_DIR"

launchctl bootout "$USER_DOMAIN" "$BACKEND_PLIST" >/dev/null 2>&1 || true
launchctl bootout "$USER_DOMAIN" "$FRONTEND_PLIST" >/dev/null 2>&1 || true

cat >"$BACKEND_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$BACKEND_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>-m</string>
    <string>uvicorn</string>
    <string>app.main:app</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>8000</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$BACKEND_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/backend.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/backend.err.log</string>
</dict>
</plist>
PLIST

cat >"$FRONTEND_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$FRONTEND_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$NODE_BIN</string>
    <string>$FRONTEND_DIR/node_modules/vite/bin/vite.js</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>5173</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$FRONTEND_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/frontend.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/frontend.err.log</string>
</dict>
</plist>
PLIST

launchctl bootstrap "$USER_DOMAIN" "$BACKEND_PLIST"
launchctl bootstrap "$USER_DOMAIN" "$FRONTEND_PLIST"
launchctl enable "$USER_DOMAIN/$BACKEND_LABEL"
launchctl enable "$USER_DOMAIN/$FRONTEND_LABEL"
launchctl kickstart -k "$USER_DOMAIN/$BACKEND_LABEL"
launchctl kickstart -k "$USER_DOMAIN/$FRONTEND_LABEL"

echo "installed and started:"
echo "  $BACKEND_LABEL -> http://127.0.0.1:8000/"
echo "  $FRONTEND_LABEL -> http://127.0.0.1:5173/"
echo "logs:"
echo "  $LOG_DIR/backend.out.log"
echo "  $LOG_DIR/backend.err.log"
echo "  $LOG_DIR/frontend.out.log"
echo "  $LOG_DIR/frontend.err.log"
