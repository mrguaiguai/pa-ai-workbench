# WeKnora Native Deployment Readiness Runbook

Date: 2026-06-23

Task: `WNX-P0-05`

Branch: `weknora-first-mvp`

## Purpose

This runbook defines the internal local production recovery path for PA AI
Workbench on the WeKnora Native Expansion branch. It is for an operator running
the checked-out repository on a trusted workstation. It is not a cloud
deployment guide.

Evidence boundary:

- Service readiness is live service/status evidence only.
- It does not upgrade document, chunk, RAG, knowledge-chat, AgentQA, Wiki, MCP,
  web search, vector store, connector, or organization workflow coverage.
- Do not commit logs, pid files, `.env` files, local databases, uploads, caches,
  `node_modules`, `dist`, screenshots, chunks, vectors, provider payloads, API
  keys, service tokens, or private endpoints.

## Runtime Stack

The internal stack is:

```text
PA frontend -> PA backend BFF -> WeKnora native adapter -> WeKnora platform
```

Required service surfaces:

- PA backend: `/health`, `/api/status`, `/api/model/status`,
  `/api/native/status`.
- PA frontend: Vite shell on localhost for operator use.
- WeKnora: reachable through PA backend status only; frontend must not call
  WeKnora directly.
- Model: chat model status must be configured and non-mock.
- Embedding: embedding status must be configured and non-mock.
- Vector store: native vector-store readiness is checked through the masked
  native status center.
- Parser: parser/readiness is represented by the
  `model_embedding_rerank_parser` capability group until `WNX-P2-01` adds
  deeper native model/parser checks.

## Manual Service Commands

Use the repository-local helper for short-lived local operation:

```bash
scripts/pa-dev-services.sh status
scripts/pa-dev-services.sh start
scripts/pa-dev-services.sh restart
scripts/pa-dev-services.sh stop
scripts/pa-dev-services.sh logs
```

The helper manages local pid files under `tmp/dev-services` and log files under
`logs/dev-services`. Those runtime directories must remain untracked.

## LaunchAgents

For durable macOS user-session operation, prefer LaunchAgents:

```bash
scripts/install-pa-launchagents.sh
scripts/uninstall-pa-launchagents.sh
```

Expected labels:

```text
com.pa-ai-workbench.backend
com.pa-ai-workbench.frontend
```

The install script writes plist files under the user's LaunchAgents directory
and uses `KeepAlive` for both backend and frontend. It writes service output to
local launchd logs; do not commit those files.

## Status Checks

After start or restart, verify status through PA only:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/model/status
curl http://127.0.0.1:8000/api/native/status
```

Healthy internal readiness means:

- `/health` returns PA backend status `ok`.
- `/api/status` shows `knowledge_backend=weknora_api`, `mock_mode=false`, and
  WeKnora connected.
- `/api/model/status` shows configured non-mock chat model and embedding.
- `/api/native/status` returns `masked=true`, `evidence_type=live_api`, 15
  capability groups, live system/workspace/model/vector readiness, and visible
  partial/backlog states where the stage is not complete.

## Validation Script

Use the WNX deployment readiness checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_deployment_readiness.py
backend/.venv/bin/python backend/scripts/check_weknora_native_deployment_readiness.py --start-services
```

Default mode checks runbook/script structure. `--start-services` starts
temporary backend/frontend processes on free localhost ports, validates live
status endpoints, checks frontend HTML response, and terminates the temporary
processes before exit.

The checker also verifies that the status center remains masked and does not
emit raw config, chunks, vectors, logs, provider payloads, or secret-shaped
values.

## Recovery Flow

When PA is unavailable:

1. Run `scripts/pa-dev-services.sh status`.
2. Run `scripts/pa-dev-services.sh restart`.
3. Recheck `/health`.
4. Recheck `/api/status`.
5. Recheck `/api/model/status`.
6. Recheck `/api/native/status`.
7. If short-lived shell services keep disappearing, switch to
   `scripts/install-pa-launchagents.sh`.

When WeKnora is unavailable:

1. Keep PA backend running so blocked state is visible.
2. Use `/api/status` and `/api/native/status` to confirm the blocked group and
   next WNX action.
3. Recover the external WeKnora app, database, Redis/task queue, DocReader,
   vector store, model provider, embedding provider, or parser service outside
   PA.
4. Rerun the WNX deployment readiness checker.

When model, embedding, vector store, or parser readiness is not live:

1. Do not switch to mock to pass readiness.
2. Treat the affected capability as blocked or partial.
3. Use the status center's `next_action` to route follow-up work.
4. Preserve the failure in the report if recovery cannot be completed.

## Rollback

If the current branch cannot recover:

```bash
scripts/pa-dev-services.sh stop
scripts/uninstall-pa-launchagents.sh
git log --oneline -5
```

Then choose the last known good local commit from the WNX progress log and
restart using the same status checks. Do not merge `main`, push, or rewrite
history as part of local readiness recovery unless the user explicitly asks.

## PASS Boundary

`WNX-P0-05` passes when the runbook commands are documented and the live service
checker proves temporary backend/frontend startup plus truthful PA status
endpoints. It does not count as live-full workflow evidence for future
`WNX-P1-*` or `WNX-P2-*` capability tasks.
