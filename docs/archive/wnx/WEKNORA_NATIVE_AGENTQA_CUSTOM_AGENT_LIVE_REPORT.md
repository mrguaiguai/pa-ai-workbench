# WeKnora Native AgentQA And Custom Agent Live Report

> Task: `WNX-P1-05`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.
>
> Decision: PASS for the native AgentQA/custom Agent workflow entry, PA
> history/output persistence, catalog visibility, and explicit citation blocker.

## Scope

This task connects WeKnora native AgentQA/custom Agent capability into PA's
intelligent analysis page and history layer.

Implemented:

- PA BFF reads WeKnora native custom Agent catalog from `/api/v1/agents`.
- PA BFF reads native type presets and placeholder groups through native Agent
  endpoints and returns only safe summary fields.
- PA BFF reads suggested questions for the selected native Agent when available.
- PA BFF runs native AgentQA through `/api/v1/agent-chat/{session_id}` after
  creating a native session.
- PA persists conversation messages, generation task, generated output, event
  counts, tool names, and warnings.
- PA saves citations only when native AgentQA emits traceable `references`
  events.
- PA records `CITATION_BLOCKED` when native AgentQA returns an answer but no
  traceable references.
- Analysis page renders a native AgentQA panel with Agent picker, catalog
  status, copy backlog status, and runtime result counts.

Not implemented as PASS:

- Agent copy/update/delete in PA. These are backlog until PA has ownership,
  confirmation, and audit behavior.
- AgentQA citation PASS. Current native AgentQA did not emit traceable
  references in the live run.

## Native Source Audit

Native routes and services inspected:

- `internal/router/router.go`
- `internal/handler/session/types.go`
- `internal/handler/session/qa.go`
- `internal/application/service/session_agent_qa.go`
- `internal/handler/custom_agent.go`
- `internal/application/service/custom_agent.go`
- `internal/types/custom_agent.go`
- `internal/event/event.go`
- `internal/event/event_data.go`
- `internal/handler/session/agent_stream_handler.go`
- `internal/types/chat.go`
- `internal/types/agent.go`

Observed native shape:

- `POST /api/v1/agent-chat/{session_id}` runs AgentQA with the same request
  shape as knowledge-chat plus `agent_enabled` and `agent_id`.
- `GET /api/v1/agents` lists built-in and custom agents.
- `GET /api/v1/agents/type-presets` exposes preset metadata.
- `GET /api/v1/agents/placeholders` exposes placeholder definitions.
- `GET /api/v1/agents/{id}/suggested-questions` exposes suggested questions.
- `POST /api/v1/agents/{id}/copy` exists but remains PA backlog for this task.
- Native AgentQA streams `answer`, `tool_call`, `tool_result`, `complete`, and
  optionally `references`.

Important blocker:

- `AgentState.KnowledgeRefs` is initialized, but the audited Agent engine path
  does not show a reliable population path for traceable references during the
  live run. The live smoke observed zero native references, so PA correctly
  persisted a citation blocker instead of fabricating citations from tool text.

## Validation

Live API smoke:

```text
WeKnora native AgentQA/custom Agent workflow
- decision: PASS
- evidence_type: live_api
- catalog: agents=4 presets=5 copy=backlog
- agentqa: answer_events=128 references=0 saved_citations=0 citation_blocked=true
- history: native_agentqa output listed
```

Live API + browser smoke:

```text
WeKnora native AgentQA/custom Agent workflow
- decision: PASS
- evidence_type: live_api
- catalog: agents=4 presets=5 copy=backlog
- agentqa: answer_events=206 references=0 saved_citations=0 citation_blocked=true
- history: native_agentqa output listed
- browser: Analysis page rendered native AgentQA workflow
```

Additional validation:

- `py_compile` passed for the adapter, service, API, schemas, and smoke script.
- Frontend `tsc --noEmit` passed.
- Frontend production build passed.

## Evidence Boundaries

Live evidence:

- PA `/api/analysis/native-agents` reached native WeKnora Agent catalog and
  returned four Agents and five type presets in the current run.
- PA `/api/analysis/native-agentqa` created a native session and streamed a live
  AgentQA answer through WeKnora.
- PA persisted a `native_agentqa` history output.
- PA displayed the native AgentQA workflow in the Analysis browser page.

Fixture evidence:

- The query text was sanitized synthetic input, processed by the live PA and
  WeKnora services.

Blocked evidence:

- Native AgentQA returned no traceable references in this run. PA recorded
  `CITATION_BLOCKED` and saved zero citations.

Backlog evidence:

- Agent copy/update/delete are deliberately left backlog for PA until an
  ownership, confirmation, and audit design exists.

Mock/cached/static evidence:

- None counted as PASS.

## Coverage Impact

`AgentQA/custom Agent` remains `live-partial`.

Reason:

- The AgentQA/custom Agent workflow is now live through PA with real output and
  history persistence.
- Citation PASS still requires traceable native references, which were absent
  in the live validation.

Coverage remains:

```text
8.75 / 15 = 58.3%
```

## Risks And Next Steps

- Native AgentQA citation mapping is blocked until WeKnora emits traceable
  `references` events or documents another native citation shape.
- Tool outputs are not accepted as citations because they can contain
  unstructured text without stable source identity.
- Agent copy/update/delete should stay backlog until PA can provide
  confirmation, ownership checks, and audit events.
- `WNX-P1-07` should unify history/citation handling across native workflows and
  keep this AgentQA blocker visible.
