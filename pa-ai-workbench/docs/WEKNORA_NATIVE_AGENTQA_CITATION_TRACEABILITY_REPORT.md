# WeKnora Native AgentQA Citation Traceability Report

Date: 2026-06-23

Task: `WNX-P3-04`

Branch: `weknora-first-mvp`

Decision: `BLOCKED`

Evidence type: audit/map, blocked evidence, live API evidence.

## Scope

`WNX-P3-04` rechecks whether AgentQA/custom Agent can move from
`live-partial` to `live-full` for the Native Expansion coverage ledger.

The required PASS condition is strict:

- native AgentQA must emit traceable references;
- PA must parse those references into evidence items;
- PA must save citations;
- history detail must expose locatable citation metadata; and
- `citation_blocked` must be false.

This task does not accept Agent answer text, tool text, old reports, cached
browser state, or fixture-only output as citation PASS evidence.

## Native Source Audit

Inspected native source files:

- `internal/router/router.go`
- `internal/handler/session/qa.go`
- `internal/application/service/session_agent_qa.go`
- `internal/handler/session/agent_stream_handler.go`
- `internal/handler/session/helpers.go`
- `internal/event/event.go`
- `internal/event/event_data.go`
- `internal/types/chat.go`
- `internal/types/agent.go`
- `internal/agent/engine.go`
- `internal/agent/finalize.go`
- `internal/agent/tools/knowledge_search.go`
- `internal/application/service/session_knowledge_qa.go`

Findings:

- Native stream responses support `response_type=references` and top-level
  `knowledge_references`.
- Ordinary knowledge QA emits `EventAgentReferences` from
  `session_knowledge_qa.go` when search results exist.
- AgentQA registers a references handler, and `AgentCompleteData` can carry
  `KnowledgeRefs`.
- The audited Agent engine initializes `AgentState.KnowledgeRefs` and forwards
  it on completion, but this audit did not find a reliable path that appends
  traceable `SearchResult` objects from Agent tools into that state during the
  live AgentQA workflow.
- Tool output text is not accepted as citation evidence because it lacks stable
  source identity and can contain unstructured answer context.

## PA Parser Audit

Inspected PA files:

- `knowledge_engine/backends/weknora_api_backend.py`
- `backend/app/services/native_agent_service.py`
- `backend/scripts/check_weknora_native_agentqa_workflow.py`
- `backend/scripts/check_weknora_native_history_citation.py`

Findings:

- PA reads AgentQA SSE events from `/api/v1/agent-chat/{session_id}`.
- PA counts every `response_type` and reads references only from real
  `response_type=references` events with `knowledge_references`.
- PA converts reference items into evidence only through the existing evidence
  builder and saves citations only from traceable evidence.
- When no traceable references are present, PA records `CITATION_BLOCKED` and
  keeps `saved_citations=0`.

No PA parser fix is justified in this task because the current live stream did
not expose traceable native AgentQA references for PA to parse.

## Live Validation

AgentQA workflow smoke:

```text
WeKnora native AgentQA/custom Agent workflow
- decision: PASS
- evidence_type: live_api
- catalog: agents=4 presets=5 copy=backlog
- agentqa: answer_events=157 references=0 saved_citations=0 citation_blocked=true
- history: native_agentqa output listed
```

History/citation smoke:

```text
WeKnora native history/citation unification
- decision: PASS
- evidence_type: live_api
- knowledge_chat: saved_citations=2 traceable=2 locator=located
- agentqa: saved_citations=0 traceable=0 citation_blocked=true
- history: filters distinguish WeKnora and citation_blocked outputs
```

The second smoke is important because it proves PA citation persistence and
locator behavior still work for native knowledge-chat in the same environment.
The AgentQA blocker is therefore not a general PA citation storage outage.

## Coverage Impact

`AgentQA/custom Agent` remains `live-partial`.

Coverage remains:

```text
11.25 / 15 = 75.0%
```

The attempted score move is not accepted:

```text
AgentQA/custom Agent live-partial -> live-full: blocked
score gain: +0.00
```

## Required Next Step

To unblock this group, a later task must make native AgentQA emit traceable
references or document another native citation shape with stable source
identity. Only after a live smoke shows `references > 0`,
`saved_citations > 0`, `citation_blocked=false`, and locatable history
citations can the coverage ledger promote this group to `live-full`.

The separate `WNX-P3-05` data source connector path remains the next small
score-moving option, but it requires a safe configured connector and explicit
operator approval for live connector workflow checks.
