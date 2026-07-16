#!/usr/bin/env bash
set -euo pipefail

LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
USER_DOMAIN="gui/$(id -u)"

BACKEND_LABEL="com.pa-ai-workbench.backend"
FRONTEND_LABEL="com.pa-ai-workbench.frontend"
BACKEND_PLIST="$LAUNCH_AGENT_DIR/$BACKEND_LABEL.plist"
FRONTEND_PLIST="$LAUNCH_AGENT_DIR/$FRONTEND_LABEL.plist"

launchctl bootout "$USER_DOMAIN" "$BACKEND_PLIST" >/dev/null 2>&1 || true
launchctl bootout "$USER_DOMAIN" "$FRONTEND_PLIST" >/dev/null 2>&1 || true
rm -f "$BACKEND_PLIST" "$FRONTEND_PLIST"

echo "uninstalled PA Workbench LaunchAgents"
