# WNID-P1-01 First-Class Intelligent Dialogue Shell Report

> Date: 2026-06-25
>
> Task: `WNID-P1-01`
>
> Evidence type: live API + live browser evidence
>
> Scope: PA product shell only; no WeKnora native source change and no WNFC
> conclusion rewrite.

## Result

`WNID-P1-01` is complete. The PA frontend now has a first-class `#/dialogue`
workspace that promotes native AgentQA out of the hidden Analysis advanced
panel and exposes Agent picker, run controls, strategy summary, tool trace,
citations, suggested-question entry, and history in the primary product shell.

Task state: `complete`.

The first sandboxed browser run was blocked because localhost port binding is
not allowed inside the restricted sandbox. After explicit user approval, the
same validation ran with permission to bind temporary localhost ports and launch
headless Chrome. The checker passed with current-run live API and browser
evidence.

## Implemented Product Surface

Changed PA frontend files:

- `frontend/src/pages/DialoguePage.tsx`;
- `frontend/src/App.tsx`;
- `frontend/src/pages/HomePage.tsx`;
- `frontend/src/styles.css`.

The new `DialoguePage` uses existing PA BFF/native paths:

- `GET /api/analysis/native-agents`;
- `POST /api/analysis/native-agentqa`;
- `GET /api/knowledge-bases/native/overview`;
- `GET /api/conversations`;
- `GET /api/conversations/{conversation_id}/messages`.

Visible first-class shell elements:

- native Agent picker;
- AgentQA run controls;
- active KB scope field and knowledge scope field;
- suggested-question chips when native suggestions are returned;
- conversation history and message stream;
- strategy summary from native Agent catalog fields;
- tool trace from AgentQA runtime fields;
- citation panel using the existing PA citation renderer.

## Native Source And PA Audit

Native source audit confirmed the reused WeKnora contract:

- `internal/handler/session/qa.go` exposes AgentQA and knowledge-qa routes;
- `internal/application/service/session_agent_qa.go` requires a custom Agent
  and builds the runtime Agent config;
- `internal/application/service/agent_service.go` registers knowledge, Wiki,
  MCP, Web Search, Web Fetch, thinking, and final-answer tools;
- `internal/handler/custom_agent.go`,
  `internal/application/service/custom_agent.go`,
  `internal/types/custom_agent.go`, and `client/agent_manage.go` expose custom
  Agent config and suggested questions;
- `client/agent.go` exposes the AgentQA request path.

PA audit confirmed no backend API change was required for this task:

- `backend/app/api/analysis.py` already exposes native Agent catalog and
  AgentQA run endpoints;
- `backend/app/services/native_agent_service.py` already persists AgentQA
  history, output, runtime metadata, and citations;
- `frontend/src/api/client.ts` already types the catalog, runtime, citation,
  and AgentQA request/response shapes.

## Validation Run

Passed:

```bash
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/typescript/bin/tsc --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vite/bin/vite.js build
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_intelligent_dialogue_shell.py
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_shell.py
```

Live browser evidence:

```text
WeKnora native intelligent dialogue shell
- decision: PASS
- task: WNID-P1-01
- evidence_type: live_api + live_browser
- api: agents=4 catalog_status=live suggestions=0 active_kb=not_configured
- browser: route=dialogue markers=8 hidden_advanced_panel=false
```

The checker starts a temporary PA backend with a temporary SQLite database,
starts a temporary Vite frontend, opens `#/dialogue` in headless Chrome, and
checks visible shell markers for Agent, History, Strategy, Tool Trace,
Citations, and run controls. Output is sanitized to counts/statuses only.

## Remaining WNID Boundaries

This task proves the first-class dialogue shell and live native Agent catalog
visibility. It does not claim completion for later WNID tasks:

- `WNID-P1-02` must still wire Quick Q&A live path from the dialogue shell.
- `WNID-P2-01` must still implement full online strategy editing.
- `WNID-P2-02` must still expand AgentQA trace/run contract evidence.
- `WNID-P3-*` and `WNID-P4-*` must still prove MCP execution and Web Search.

## Non-Changes

- No WNFC spec or completion conclusion changed.
- No WeKnora Go source changed.
- No backend BFF route changed.
- No `.env`, database, log, upload, `node_modules`, or `dist` artifact was
  staged.
- `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` was not touched.
