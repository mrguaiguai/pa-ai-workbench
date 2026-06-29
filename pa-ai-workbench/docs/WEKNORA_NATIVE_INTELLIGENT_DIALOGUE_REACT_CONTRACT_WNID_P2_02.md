# WNID-P2-02 ReACT Reasoning Trace And Run Contract Report

> Date: 2026-06-25
>
> Task: `WNID-P2-02`
>
> Evidence type: live API + live browser evidence
>
> Scope: PA run-contract mapping for WeKnora native AgentQA/ReACT stream
> events; no WeKnora native source change and no WNFC conclusion rewrite.

## Result

`WNID-P2-02` is complete. PA now exposes a structured native AgentQA run
contract for ReACT dialogue runs. The contract records WeKnora stream event
types and counts, selected Agent strategy summary, conversation continuity,
tool names, references, citation persistence, and completion status without
storing raw tool arguments, tool results, provider payloads, or credentials.

Task state: `complete`.

## Implemented Product Surface

Changed PA files:

- `knowledge_engine/backends/weknora_api_backend.py`;
- `backend/app/services/native_agent_service.py`;
- `backend/app/schemas.py`;
- `frontend/src/api/client.ts`;
- `frontend/src/pages/DialoguePage.tsx`;
- `backend/scripts/check_weknora_native_intelligent_dialogue_react_contract.py`.

The dialogue page now exposes:

- `Run Contract` state in the AgentQA Tool Trace panel;
- structured event counts for `thinking`, `tool_call`, `tool_result`,
  `references`, `answer`, and `complete`;
- selected native Agent identity, Agent type, and safe strategy summary;
- PA conversation continuity count and persisted user/assistant message ids;
- citations and reference counts beside the run contract.

## Native Source Audit

Native WeKnora source audit confirmed that PA can use the existing AgentQA
stream contract:

- `internal/handler/session/agent_stream_handler.go` maps Agent events into
  SSE response types including `thinking`, `tool_call`, `tool_result`,
  `references`, `answer`, `reflection`, `error`, and `complete`;
- the same handler maps MCP approval events to
  `tool_approval_required` and `tool_approval_resolved`;
- `internal/application/service/session_agent_qa.go` resolves the selected
  custom Agent, builds the runtime Agent config, loads multi-turn history when
  enabled, and executes the Agent engine;
- `client/agent.go` and `client/session.go` expose the Agent stream response
  shape used by PA's adapter.

No native Go source change was required for this task.

## PA Contract

PA adapter changes:

- collects the AgentQA stream event sequence, capped to safe metadata;
- counts event types and extracts completion metadata such as total steps and
  total duration when WeKnora emits it;
- returns `event_contract` with booleans for answer, completion, ReACT trace,
  and tool call/result balance;
- collects tool names only from event metadata and does not persist tool
  arguments or raw tool output.

PA service/schema changes:

- persists `run_contract`, `event_sequence`, `selected_agent`, and
  `conversation_continuity` in runtime and output JSON;
- stores the same safe contract summary in assistant message metadata;
- keeps selected Agent strategy summary to field names/counts/booleans and does
  not duplicate raw prompt/context text into the run contract;
- keeps PA citations as the proof channel for native references.

## Validation Run

Passed:

```bash
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_intelligent_dialogue_react_contract.py backend/app/services/native_agent_service.py backend/app/schemas.py knowledge_engine/backends/weknora_api_backend.py
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/typescript/bin/tsc --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vite/bin/vite.js build
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_react_contract.py
```

Live evidence:

```text
WeKnora native intelligent dialogue ReACT contract
- decision: PASS
- task: WNID-P2-02
- evidence_type: live_api + live_browser
- api: agentqa=live thinking=84 tool_call=9 tool_result=4 references=5 answer=716 complete=true citations=5 continuity=passed selected_agent=present
- browser: route=dialogue run_contract=visible markers=10 hidden_advanced_panel=false
```

The checker starts temporary PA backend/frontend services, uploads a sanitized
document through PA, waits for native indexing, runs native AgentQA with the
selected native Agent and native document scope, verifies ReACT
thinking/tool_call/tool_result/answer/complete events, verifies saved PA
citations are present, verifies PA conversation continuity and history, then
drives `#/dialogue` in headless Chrome until the Run Contract markers render.

## Remaining WNID Boundaries

This task proves native AgentQA run-contract visibility and PA continuity for
ReACT events. It does not claim completion for later tasks:

- `WNID-P3-*` must still prove real MCP tools/resources/prompts read and
  approval-gated MCP tool execution.
- `WNID-P4-*` must still prove Web Search provider setup and AgentQA Web Search
  references.
- `WNID-P5-01` must still prove Wiki Mode Agent workflows.
- `WNID-P6-01` must still prove suggested questions can launch a live answer.

## Non-Changes

- No WNFC spec or completion conclusion changed.
- No WeKnora Go source changed.
- No MCP tool execution or Web Search answer PASS is claimed.
- No `.env`, database, log, upload, `node_modules`, `dist`, screenshot, raw
  provider payload, raw tool output, or credential was staged.
- `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` was not touched.
