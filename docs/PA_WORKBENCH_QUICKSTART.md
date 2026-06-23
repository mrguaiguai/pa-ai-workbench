# PA + WeKnora Workbench Quickstart

This repository is intended to be used as one collaborative worktree:

```text
WeKnora native platform -> PA backend BFF -> PA frontend workbench
```

The goal is a fresh clone that can be configured and started with repository
scripts, while keeping all local credentials and runtime data out of Git.

## Prerequisites

- Git
- Docker Desktop or Docker Engine with Docker Compose
- Python 3.11+
- Node.js 18+ and npm

## First Run

From the repository root:

```bash
./scripts/pa-workbench-setup.sh
./scripts/pa-workbench-start.sh
./scripts/pa-workbench-check.sh
```

The setup script creates these local files when missing:

```text
.env
pa-ai-workbench/backend/.env
pa-ai-workbench/frontend/.env.local
```

These files are intentionally ignored by Git. Put real provider keys, service
tokens, private endpoints, workspace IDs, and knowledge-base IDs only in local
env files or your shell environment.

## Service URLs

Default local URLs:

| Service | URL |
| --- | --- |
| WeKnora frontend | `http://127.0.0.1/` |
| WeKnora app API | `http://127.0.0.1:8080` |
| PA frontend | `http://127.0.0.1:5173/` |
| PA backend | `http://127.0.0.1:8000` |

`scripts/pa-workbench-check.sh` verifies health/status endpoints without
printing raw payloads.

## PA Native Mode

PA can start in mock mode from `pa-ai-workbench/backend/.env.example`, but the
WeKnora-first internal-production workflow requires live native configuration.
Set these in `pa-ai-workbench/backend/.env` after the WeKnora runtime is ready:

```text
KNOWLEDGE_BACKEND=weknora_api
MOCK_MODE=false
WEKNORA_BASE_URL=http://127.0.0.1:8080
WEKNORA_SERVICE_TOKEN=
WEKNORA_WORKSPACE_ID=
WEKNORA_DEFAULT_KB_ID=
```

Fill the service token, workspace ID, and knowledge-base ID locally. Also
configure real non-mock chat and embedding providers before claiming live PASS
evidence. Mock mode is acceptable for UI exploration, but it is not PASS
evidence for WeKnora-native capability work.

## Common Commands

```bash
# Start everything
./scripts/pa-workbench-start.sh

# Start only PA backend/frontend
./scripts/pa-workbench-start.sh --skip-weknora

# Start only WeKnora Docker services
./scripts/pa-workbench-start.sh --skip-pa

# Rebuild WeKnora Docker images before starting
./scripts/pa-workbench-start.sh --build

# Check local readiness
./scripts/pa-workbench-check.sh

# Stop PA services
pa-ai-workbench/scripts/pa-dev-services.sh stop

# Stop WeKnora Docker services
docker compose down
```

## Collaboration Rules

- Do not commit `.env`, databases, logs, uploads, `node_modules`, `dist`,
  screenshots, provider payloads, API keys, service tokens, passwords, private
  endpoints, or private key material.
- Keep WeKnora native capability changes and PA adapter/product changes in the
  same pull request when they are required together.
- Keep PA frontend calls behind the PA backend BFF. The browser should not call
  WeKnora native APIs directly.
- Treat mock, fixture-only, cached browser state, static UI, and old reports as
  development aids only. They do not count as live PASS evidence.

## Monorepo Migration Note

The current local checkout contains a nested Git repository at:

```text
pa-ai-workbench/.git
```

Do not run `git add .` from the outer repository until this is resolved. If PA
should be a normal directory in the outer GitHub repository, first choose one of
these maintainer actions:

1. preserve PA history with a subtree/filter-repo migration, then remove the
   nested `.git`; or
2. intentionally flatten PA into the outer repo without preserving its separate
   Git history, after making a backup and confirming the current PA branch is
   pushed or otherwise recoverable.

Until then, keep using the PA repository's own `git status` for PA commits and
save native WeKnora patches in tracked docs or in a dedicated outer Git branch.
