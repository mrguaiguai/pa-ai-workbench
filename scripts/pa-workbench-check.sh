#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WEKNORA_APP_URL="${WEKNORA_APP_URL:-http://127.0.0.1:8080}"
WEKNORA_FRONTEND_URL="${WEKNORA_FRONTEND_URL:-http://127.0.0.1:80}"
PA_API_URL="${PA_API_URL:-http://127.0.0.1:8000}"
PA_FRONTEND_URL="${PA_FRONTEND_URL:-http://127.0.0.1:5173}"

log() {
  printf '[pa-check] %s\n' "$1"
}

check_url() {
  local label="$1"
  local url="$2"
  if curl -fsS --max-time 8 "$url" >/dev/null; then
    log "PASS $label"
  else
    log "FAIL $label ($url)"
    return 1
  fi
}

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

errors=0
check_url "WeKnora app health" "$WEKNORA_APP_URL/health" || errors=$((errors + 1))
check_url "WeKnora frontend" "$WEKNORA_FRONTEND_URL/" || errors=$((errors + 1))
check_url "PA backend health" "$PA_API_URL/health" || errors=$((errors + 1))
check_url "PA backend status" "$PA_API_URL/api/status" || errors=$((errors + 1))
check_url "PA native status" "$PA_API_URL/api/native/status" || errors=$((errors + 1))
check_url "PA frontend" "$PA_FRONTEND_URL/" || errors=$((errors + 1))

if [[ "$errors" -ne 0 ]]; then
  log "one or more checks failed"
  log "logs: pa-ai-workbench/scripts/pa-dev-services.sh logs"
  exit 1
fi

log "all checks passed"
log "PA: $PA_FRONTEND_URL"
log "WeKnora: $WEKNORA_FRONTEND_URL"
