# WeKnora-First Native AgentQA Live Report

> Task: `WF-P1-01`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: live API with explicit citation blocker.

## Scope

`WF-P1-01` adds the smallest PA adapter slice for WeKnora native AgentQA/custom
Agent. PA now calls native WeKnora AgentQA through `/api/v1/agent-chat/{session_id}`,
stores the native answer through PA's output/history model, and records a
citation blocker when native AgentQA does not emit traceable references.

This report does not claim citation mapping PASS. The current live AgentQA
response produced answer events but no reference events, so saved citations
remain `0` and the blocker is part of the result.

## Native Source And PA Mapping

| Area | Source | Finding | Decision |
| --- | --- | --- | --- |
| Native AgentQA route | `internal/router/router.go` | `POST /api/v1/agent-chat/{session_id}` routes to `AgentQA`. | Use as native AgentQA entry. |
| Native request shape | `internal/handler/session/types.go`, `internal/handler/session/qa.go` | Request uses `query`, `agent_enabled`, `agent_id`, `knowledge_base_ids`, and optional `disable_title`. | PA adapter sends the smallest safe request. |
| Native session route | `internal/handler/session/handler.go` | `POST /api/v1/sessions` creates a session container before AgentQA. | PA adapter creates a native session for the smoke. |
| Native stream shape | `internal/handler/session/helpers.go`, `internal/types/chat.go` | SSE messages use `response_type`; relevant types include `answer`, `references`, `tool_call`, `tool_result`, `error`, and `complete`. | PA adapter parses answer events and reference events only. |
| Custom Agent list | `internal/router/router.go`, `internal/handler/custom_agent.go` | `GET /api/v1/agents` lists builtin/custom agents. | PA adapter verifies the selected agent exists before execution. |
| PA adapter | `knowledge_engine/backends/weknora_api_backend.py` | Added `list_agents`, `create_agent_session`, and `run_agent_qa`. | Keep PA as a thin native API client, not a replacement Agent engine. |
| PA persistence smoke | `backend/scripts/smoke_weknora_agentqa_native_live.py` | Stores answer output in a temporary PA database and saves citations only if references are traceable. | Missing references become explicit `CITATION_BLOCKED`. |

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_agentqa_native_live.py
```

Result summary:

```text
WeKnora native AgentQA smoke passed (live)
- base URL: http://127.0.0.1:8080
- knowledge base: 29adf20a-91db-45b5-9df1-6c608f802e8d
- agent id: builtin-wiki-researcher
- session created: True
- answer stored: True
- answer chars: 368
- native reference count: 0
- saved citations: 0
- citation blocker: CITATION_BLOCKED: native AgentQA returned a live answer but did not emit traceable references with source_type/evidence_id/native ids.
- event types: agent_query,answer,complete,tool_call,tool_result
```

What this proves:

- PA called real WeKnora native AgentQA through the native AgentQA endpoint.
- PA used a real configured WeKnora workspace and knowledge base.
- PA used non-mock chat and embedding runtime posture.
- WeKnora emitted a live native answer stream.
- PA stored the answer through its output/history model in a temporary database.
- Native AgentQA did not emit traceable references in this run, so PA saved no
  citations and recorded an explicit citation blocker.

## Citation Contract Decision

| Field | Requirement | Live result |
| --- | --- | --- |
| `source` | Required for saved citations. | Blocked because no native references were emitted. |
| `source_type` | Required for saved citations. | Blocked because no native references were emitted. |
| `evidence_id` | Required for saved citations. | Blocked because no native references were emitted. |
| `chunk_id` / `external_doc_id` / `wiki_page_id` | Required when source type needs them. | Blocked because no native references were emitted. |
| Answer/history storage | Required for this adapter slice. | PASS. |
| Citation mapping | Required only when native references are traceable. | Explicit blocker, not citation PASS. |

PA does not invent fake `source_type`, `evidence_id`, `chunk_id`,
`external_doc_id`, or `wiki_page_id`. Missing native references remain blocked.

## Evidence Classification

| Evidence category | Result |
| --- | --- |
| live | Used for native AgentQA endpoint, native session creation, answer stream, and PA output persistence. |
| fixture-only | Not used as completion evidence. |
| mock | Not used; mock evidence is not PASS. |
| cached | Not used; old reports and old stream output are not PASS. |
| partial | Citation mapping is partial/blocked because native references were absent. |
| blocked | Citation mapping is blocked until native AgentQA emits traceable references or PA receives a documented native citation shape. |
| backlog | Frontend AgentQA browser integration and richer custom Agent selection remain later slices. |

## Blocked And Backlog Decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Core native AgentQA call | Completed | Live SSE stream returned answer events and completed without error. |
| PA answer/history storage | Completed | Smoke persisted a completed PA output in a temporary database. |
| Citation mapping | Blocked inside completed adapter slice | Native stream emitted no `references` event; PA cannot create traceable citations without native ids. |
| `builtin-smart-reasoning` route | Blocked for this run | A read-only probe exceeded the current timeout window; it is not reliable enough for this task's PASS. |
| Frontend page integration | Backlog | No frontend files changed; browser validation belongs to a later frontend polish slice. |

## PASS Statement

`WF-P1-01` is completed for the smallest native AgentQA adapter slice: PA calls
native AgentQA, receives and stores a live answer, and fails closed on missing
citations. The citation side is explicitly blocked, not treated as PASS. Future
work should either select/configure an AgentQA path that emits references, or
document WeKnora's native citation response shape and map it to PA's
`source_type`, `evidence_id`, `chunk_id`, `external_doc_id`, and `wiki_page_id`
contract.
