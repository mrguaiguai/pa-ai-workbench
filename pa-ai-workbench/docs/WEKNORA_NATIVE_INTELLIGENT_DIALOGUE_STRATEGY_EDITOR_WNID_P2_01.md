# WNID-P2-01 ReACT And Custom Agent Strategy Editor Report

> Date: 2026-06-25
>
> Task: `WNID-P2-01`
>
> Evidence type: live API + live browser + audit evidence
>
> Scope: PA strategy editor for WeKnora native custom Agent config; no WeKnora
> native source change and no WNFC conclusion rewrite.

## Result

`WNID-P2-01` is complete. PA now exposes a confirmation-gated native custom
Agent strategy editor in the first-class `#/dialogue` workspace. The editor can
view and update WeKnora native strategy fields for prompt, context template,
allowed tools, MCP selection, Web Search flags, web fetch settings,
multi-turn/history, retrieval thresholds, rerank thresholds, and suggested
prompts. Strategy mutations use `NativeMutationAudit`.

Task state: `complete`.

## Implemented Product Surface

Changed PA files:

- `knowledge_engine/backends/weknora_api_backend.py`;
- `backend/app/api/analysis.py`;
- `backend/app/services/native_agent_service.py`;
- `backend/app/schemas.py`;
- `frontend/src/api/client.ts`;
- `frontend/src/pages/DialoguePage.tsx`;
- `frontend/src/styles.css`;
- `backend/scripts/check_weknora_native_intelligent_dialogue_strategy_editor.py`.

The dialogue page now exposes:

- strategy field loading from native Agent catalog;
- prompt and context template editing;
- allowed tools, MCP selection mode, selected MCP service ids, and suggested
  prompts editing;
- Web Search and web fetch config fields as editable strategy config;
- multi-turn/history turn controls;
- embedding top-k, keyword threshold, vector threshold, rerank top-k, and
  rerank threshold controls;
- confirmation-gated save through PA BFF;
- compact strategy save status in the Strategy panel.

## Native Source And PA Audit

Native source audit confirmed the reused WeKnora contract:

- `internal/types/custom_agent.go` defines the required
  `CustomAgentConfig` fields: `system_prompt`, `context_template`,
  `allowed_tools`, `mcp_selection_mode`, `mcp_services`,
  `web_search_enabled`, `web_search_provider_id`, `web_fetch_enabled`,
  `web_fetch_top_n`, `multi_turn_enabled`, `history_turns`,
  `embedding_top_k`, `keyword_threshold`, `vector_threshold`,
  `rerank_top_k`, `rerank_threshold`, and `suggested_prompts`;
- `internal/handler/custom_agent.go` exposes `PUT /api/v1/agents/{id}`;
- `internal/application/service/custom_agent.go` updates custom Agent config
  and supports tenant-specific built-in Agent config records;
- `client/agent_manage.go` mirrors the same strategy fields in `AgentConfig`.

PA implementation uses the native path:

- `knowledge_engine/backends/weknora_api_backend.py` adds
  `update_agent_strategy`, a strategy-specific adapter method that preserves
  Web Search strategy fields instead of using the older WNFC CRUD helper that
  forcibly disables Web Search;
- `backend/app/services/native_agent_service.py` returns safe strategy config
  in the Agent catalog and adds `update_native_agent_strategy`;
- `backend/app/api/analysis.py` exposes
  `PUT /api/analysis/native-agents/{agent_id}/strategy`;
- `backend/app/schemas.py` and `frontend/src/api/client.ts` type the strategy
  config and mutation request;
- `frontend/src/pages/DialoguePage.tsx` renders and saves the strategy editor.

Audit safety:

- strategy update requires `confirm_token=CONFIRM_NATIVE_AGENT_MUTATION`;
- request summaries record field names, counts, and booleans only;
- reports and checker output do not print raw prompt/context values.

## Validation Run

Passed:

```bash
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_intelligent_dialogue_strategy_editor.py backend/app/api/analysis.py backend/app/services/native_agent_service.py backend/app/schemas.py knowledge_engine/backends/weknora_api_backend.py
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/typescript/bin/tsc --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vite/bin/vite.js build
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_strategy_editor.py
```

Live evidence:

```text
WeKnora native intelligent dialogue strategy editor
- decision: PASS
- task: WNID-P2-01
- evidence_type: live_api + live_browser + audit
- api: strategy_update=live updated_fields=14 audit=succeeded catalog=persisted
- browser: route=dialogue strategy_editor=visible markers=7 hidden_advanced_panel=false
- cleanup: temporary_agent_deleted=true
```

The checker starts temporary PA backend/frontend services, creates an isolated
native custom Agent, verifies a bad confirmation token blocks strategy update,
updates strategy fields with confirmation, verifies the updated strategy is
persisted in the native Agent catalog, confirms the custom Agent audit event,
opens `#/dialogue` in headless Chrome, checks strategy-editor markers, and
deletes the temporary Agent.

## Remaining WNID Boundaries

This task proves strategy view/edit/persist/audit and browser visibility. It
does not claim completion for later tasks:

- `WNID-P2-02` must still prove ReACT reasoning trace and run contract.
- `WNID-P3-*` must still prove real MCP tool/resource/prompt read and
  approval-gated tool execution.
- `WNID-P4-*` must still prove Web Search provider setup and AgentQA Web Search
  references.
- `WNID-P6-01` must still prove suggested questions can launch a live answer.

## Non-Changes

- No WNFC spec or completion conclusion changed.
- No WeKnora Go source changed.
- No MCP tool execution or Web Search answer PASS is claimed.
- No `.env`, database, log, upload, `node_modules`, `dist`, screenshot, or raw
  provider payload was staged.
- `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` was not touched.
