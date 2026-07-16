# WeKnora Native Deployment Readiness Report

Date: 2026-06-23

Task: `WNX-P0-05`

Branch: `weknora-first-mvp`

## Scope

This report validates internal local production readiness for PA AI Workbench on
the WeKnora Native Expansion branch. It proves service recovery and truthful
status surfaces, not new business workflow coverage.

Evidence type: `live service/status evidence`.

## Implemented Artifacts

- `backend/scripts/check_weknora_native_deployment_readiness.py`
- `docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md`

The checker validates recovery scripts, LaunchAgent entry points, frontend dev
and build entry points, the runbook, and optional live temporary
backend/frontend startup.

## Static Readiness Evidence

Command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_deployment_readiness.py
```

Observed result:

```text
WeKnora native deployment readiness
- decision: PASS
- mode: static
- required deployment artifacts: PASS - 10 files present
- service recovery scripts: PASS - manual and LaunchAgent recovery paths present
- frontend recovery entrypoints: PASS - node, Vite dev, and build entrypoints present
- deployment readiness runbook: PASS - operator commands and status checks documented
```

## Live Service Evidence

Command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_deployment_readiness.py --start-services
```

Observed result:

```text
WeKnora native deployment readiness
- decision: PASS
- mode: live-services
- required deployment artifacts: PASS - 10 files present
- service recovery scripts: PASS - manual and LaunchAgent recovery paths present
- frontend recovery entrypoints: PASS - node, Vite dev, and build entrypoints present
- deployment readiness runbook: PASS - operator commands and status checks documented
- /health: PASS - backend health ok
- /api/status: PASS - weknora connected; kb_mapping=validated
- /api/model/status: PASS - chat=openai_compatible; embedding=openai_compatible
- /api/native/status: PASS - 15 masked groups; vector/model/parser group live; backlog remains visible
- frontend service: PASS - Vite frontend responded with PA shell HTML
```

The live mode starts temporary backend and frontend processes on free localhost
ports and terminates them before exit. It does not install LaunchAgents, write
operator logs, modify `.env`, or commit runtime output.

## Recovery Coverage

| Area | Evidence | Decision |
| --- | --- | --- |
| Backend start/check | Temporary backend served `/health`, `/api/status`, `/api/model/status`, and `/api/native/status`. | PASS |
| Frontend start/check | Temporary Vite frontend served the PA shell HTML. | PASS |
| WeKnora reachability | `/api/status` reported WeKnora connected and KB mapping validated. | PASS |
| Model | `/api/model/status` reported configured non-mock chat provider. | PASS |
| Embedding | `/api/model/status` reported configured non-mock embedding provider. | PASS |
| Vector store | `/api/native/status` reported the vector-store capability group live. | PASS |
| Parser | `/api/native/status` reported the combined model/embedding/rerank/parser capability group live; deeper native parser checks remain scoped to `WNX-P2-01`. | PASS for P0 readiness |
| Durable local recovery | Runbook and scripts document `pa-dev-services.sh` and LaunchAgent install/uninstall paths. | PASS |

## PASS Boundary

`WNX-P0-05` upgrades the system health/status/deployment group to
`live-full` for internal local production readiness. It does not upgrade
document lifecycle, chunk management, knowledge-chat, AgentQA/custom Agent,
native Wiki, MCP, web search, vector store management, model/parser management,
data connectors, FAQ/tags/favorites/skills, or history/citation workflow
coverage.

No `.env` values, API keys, service tokens, provider payloads, raw logs,
databases, uploads, screenshots, chunks, vectors, or private endpoints are
included in this report.
