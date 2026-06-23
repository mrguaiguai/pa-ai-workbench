# WeKnora Native AgentQA Reference Propagation Patch Report

Date: 2026-06-23

Task: `WNX-P3-06`

Branch: `weknora-first-mvp`

Decision: `BLOCKED`

Evidence type: native source patch draft, audit/map evidence, live API blocked
evidence.

## Scope

`WNX-P3-06` attempts the smallest real AgentQA citation unblock after
`WNX-P3-04` proved that PA is not missing an already-emitted references event.

The required PASS condition is unchanged:

- native AgentQA emits traceable `references`;
- PA parses those references into evidence;
- PA saves citations;
- history detail exposes locatable citations; and
- `citation_blocked=false`.

Agent answer text, tool output text, old reports, cached state, and fixture-only
proof are not accepted as citation PASS evidence.

## Native Patch Draft

Inspected native files:

- `internal/router/router.go`
- `internal/handler/session/qa.go`
- `internal/application/service/session_agent_qa.go`
- `internal/handler/session/agent_stream_handler.go`
- `internal/event/event.go`
- `internal/event/event_data.go`
- `internal/types/chat.go`
- `internal/types/agent.go`
- `internal/agent/engine.go`
- `internal/agent/act.go`
- `internal/agent/finalize.go`
- `internal/agent/tools/knowledge_search.go`

Local native source patch drafted outside the PA git repository:

- `internal/agent/engine.go`
- `internal/agent/act.go`
- `internal/agent/tools/knowledge_search.go`
- `internal/agent/act_references_test.go`

The patch shape is narrow:

- `knowledge_search` structured `Data["results"]` now includes
  `knowledge_base_id`, `chunk_index`, and `score`.
- Agent tool execution extracts references only from structured
  `knowledge_search` result items.
- Extracted references require stable `chunk_id` and `knowledge_id`.
- References are deduplicated into `AgentState.KnowledgeRefs`.
- The agent emits `EventAgentReferences`, which the existing session stream
  handler serializes as a standard `response_type=references` event.

This deliberately avoids parsing answer text or free-form tool output.

## Repository And Runtime Blockers

The patch could not be accepted as a score-moving PASS in this task because:

- `/Users/mac/Downloads/WeKnora-main` is not a git repository, while the active
  branch lives only under `/Users/mac/Downloads/WeKnora-main/pa-ai-workbench`.
- The local native source patch is therefore not commit-trackable on
  `weknora-first-mvp` from the PA repository.
- The shell has no `go` or `gofmt`, so native Go formatting and focused unit
  tests could not run.
- The currently running live WeKnora service did not absorb the local native
  source patch during validation.

## Live Validation

AgentQA workflow smoke:

```text
WeKnora native AgentQA/custom Agent workflow
- decision: PASS
- evidence_type: live_api
- catalog: agents=4 presets=5 copy=backlog
- agentqa: answer_events=186 references=0 saved_citations=0 citation_blocked=true
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

The history smoke again proves PA citation persistence and locators work for
native knowledge-chat in the same environment. The AgentQA blocker remains at
the native reference/runtime layer.

## Coverage Impact

`AgentQA/custom Agent` remains `live-partial`.

Coverage remains:

```text
11.25 / 15 = 75.0%
```

No score is added from a non-live, non-commit-trackable native patch draft.

## Required Next Step

To turn this into PASS, the native patch must be applied in a commit-trackable
WeKnora source repository or equivalent tracked patch workflow, formatted and
tested with Go tooling, deployed/restarted into the live runtime, then validated
again through the PA live AgentQA and history citation smokes.

Follow-up `WNX-P3-07` completed the local Docker Go formatting/test and app
runtime rebuild/recreate path, but live AgentQA still returned zero references
and zero saved citations. The remaining blocker is therefore the live Agent
tool invocation/result/reference retention path, not host Go tooling alone.

Only a current live run with `references > 0`, `saved_citations > 0`,
`citation_blocked=false`, and locatable history citations may promote
AgentQA/custom Agent to `live-full`.
