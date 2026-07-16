#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLATFORM_ROOT="$REPOSITORY_ROOT/platform/weknora"
PA_COMMAND_DIR="$REPOSITORY_ROOT/scripts/dev"

START_WEKNORA=1
START_PA=1
BUILD_IMAGES=0
COMPOSE_PROFILES=()

for arg in "$@"; do
  case "$arg" in
    --skip-weknora)
      START_WEKNORA=0
      ;;
    --skip-pa)
      START_PA=0
      ;;
    --build)
      BUILD_IMAGES=1
      ;;
    --profile=*)
      COMPOSE_PROFILES+=("${arg#--profile=}")
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/dev/pa-workbench-start.sh [--build] [--skip-weknora] [--skip-pa] [--profile=NAME]

Start the local WeKnora stack and PA Workbench services.

This script does not print env values. Use scripts/dev/pa-workbench-setup.sh first
when dependencies or local env files are missing.
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
  printf '[pa-start] %s\n' "$1"
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Docker Compose is not available" >&2
    exit 1
  fi
}

"$SCRIPT_DIR/pa-workbench-setup.sh" --skip-install

if [[ "$START_WEKNORA" -eq 1 ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required to start WeKnora" >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Docker is installed but not running" >&2
    exit 1
  fi
  compose_args=(-f "$REPOSITORY_ROOT/infra/compose/weknora.yaml")
  for profile in "${COMPOSE_PROFILES[@]}"; do
    compose_args+=(--profile "$profile")
  done
  compose_args+=(up -d)
  if [[ "$BUILD_IMAGES" -eq 1 ]]; then
    compose_args+=(--build)
  fi
  log "starting WeKnora with Docker Compose"
  (
    cd "$REPOSITORY_ROOT"
    compose_cmd "${compose_args[@]}"
  )
fi

if [[ "$START_PA" -eq 1 ]]; then
  log "starting PA backend/frontend"
  "$PA_COMMAND_DIR/pa-dev-services.sh" start
fi

log "start command finished"
log "check: scripts/validation/check-pa-services.sh"
