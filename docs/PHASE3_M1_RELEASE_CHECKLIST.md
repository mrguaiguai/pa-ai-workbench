# PHASE3 M1 Release Checklist

Task: P3-M1-F5
Date: 2026-06-09

## Scope

This checklist gates the PA AI Workbench M1 internal pilot. M1 release requires
real WeKnora-backed RAG / Wiki capability through the PA KnowledgeBackend
Adapter. Mock paths may remain available for local development, but they cannot
be counted as M1 release evidence.

## Release Decision

Current decision: `READY`

Readiness basis: local M1 WeKnora runtime is configured with mock mode disabled,
required WeKnora settings present, and all live release smoke gates passing.

## Required Runtime Configuration

The M1 pilot runtime must set these values outside git, for example in
deployment environment variables or an untracked `backend/.env` file:

```text
KNOWLEDGE_BACKEND=weknora_api
MOCK_MODE=false
WEKNORA_BASE_URL=<weknora-base-url>
WEKNORA_SERVICE_TOKEN=<service-token>
WEKNORA_WORKSPACE_ID=<workspace-id>
WEKNORA_DEFAULT_KB_ID=<knowledge-base-id>
WEKNORA_TIMEOUT_SECONDS=60
```

Do not commit concrete service tokens, workspace IDs, KB IDs, model credentials,
pilot documents, uploads, databases, logs, or generated build artifacts.

## Gates

| Gate | Required result | Current local status |
| --- | --- | --- |
| Config mode | `KNOWLEDGE_BACKEND=weknora_api`, `MOCK_MODE=false` | Passed. |
| WeKnora service config | base URL, service token, workspace, KB, timeout present | Passed. |
| WeKnora connection smoke | health/auth/workspace/KB pass | Passed. |
| RAG smoke | uploaded sanitized doc retrieves `source=weknora_api` `document_chunk` evidence | Passed. |
| Agent smoke | QA / policy / case each persist non-mock WeKnora citations | Passed. |
| Wiki smoke | publish -> retrieve returns `source_type=wiki_page` evidence | Passed. |
| Frontend build/browser | build passes and main pages render missing-config/WeKnora states | Passed in P3-M1-F4. |
| Git safety | no `.env`, uploads, DBs, logs, `dist`, `node_modules`, API keys, or real material staged/tracked | Passed for this release-check commit. |

Latest full checker result:

```text
M1 release readiness
- decision: READY
- Config mode: PASS
- WeKnora config: PASS
- Smoke scripts: PASS
- Git safety: PASS
- WeKnora connection: PASS
- RAG smoke: PASS
- Agent smoke: PASS
- Wiki smoke: PASS
```

## Commands

Run the static release checker:

```bash
backend/.venv/bin/python backend/scripts/check_m1_release.py
```

Run full release readiness after importing live WeKnora configuration:

```bash
backend/.venv/bin/python backend/scripts/check_m1_release.py --run-live-smokes
```

Run individual gates when debugging:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_connection.py
backend/.venv/bin/python backend/scripts/smoke_weknora_rag_m1.py
backend/.venv/bin/python backend/scripts/smoke_weknora_agent_m1.py
backend/.venv/bin/python backend/scripts/smoke_weknora_wiki_m1.py
```

Check git safety before any release commit:

```bash
git status --short
git status --ignored --short
```

## Sensitive File Rules

Release is blocked if any of these are tracked, staged, or included in an
artifact intended for git:

```text
.env
backend/data/
backend/uploads/
logs/
*.db
*.sqlite
*.sqlite3
*.log
frontend/dist/
frontend/node_modules/
backend/.venv/
API keys
WeKnora service tokens
real or unsanitized pilot documents
unredacted model prompts or long evidence chunks
```

Ignored local artifacts may appear in `git status --ignored --short`; they must
remain unstaged.

## Rollback

If live WeKnora checks fail during the pilot:

1. Stop new pilot uploads.
2. Preserve logs only in the approved runtime location, not in git.
3. Switch the pilot environment back to the last known good deployment.
4. Keep local development mock mode available separately, but do not present mock
   output as M1 release evidence.
5. Re-run `check_m1_release.py --run-live-smokes` before resuming the pilot.
