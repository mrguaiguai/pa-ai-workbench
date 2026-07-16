# WeKnora Native AgentQA Runtime Validation Report

Date: 2026-06-23

Task: `WNX-P3-07`

Branch: `weknora-first-mvp`

Decision: `BLOCKED`

Evidence type: native Go test evidence, Docker runtime deployment evidence, live
API blocked evidence.

## Scope

`WNX-P3-07` validates the local native AgentQA reference propagation patch from
`WNX-P3-06` with an available Go toolchain, builds it into the local WeKnora
runtime image, restarts only the app container, and reruns the PA live AgentQA
and history citation smokes.

The required PASS condition is unchanged:

- native AgentQA emits traceable `references`;
- PA parses those references into evidence;
- PA saves citations;
- history detail exposes locatable citations; and
- `citation_blocked=false`.

Agent answer text, free-form tool output, cached reports, and fixture-only
proof are not accepted as citation PASS evidence.

## Native Runtime Validation

The host shell still has no local `go` or `gofmt`, so this task used the
existing Docker image `golang:1.26.0` instead of installing a host toolchain.

Validated native patch files:

- `internal/agent/engine.go`
- `internal/agent/act.go`
- `internal/agent/tools/knowledge_search.go`
- `internal/agent/act_references_test.go`

Go formatting completed through Docker `gofmt`.

Focused native unit tests passed:

```text
go test ./internal/agent -run 'TestExtractKnowledgeReferencesFromToolResult|TestAppendUniqueKnowledgeReferences'
ok github.com/Tencent/WeKnora/internal/agent
```

Production image build completed through Docker Compose:

```text
docker compose -f docker-compose.yml build app
Image wechatopenai/weknora-app:latest Built
```

The local `WeKnora-app` container was then recreated with `--no-deps`, leaving
the database and other services untouched. The app health endpoint returned:

```text
{"status":"ok"}
```

## Live Validation

AgentQA workflow smoke after the rebuilt runtime:

```text
WeKnora native AgentQA/custom Agent workflow
- decision: PASS
- evidence_type: live_api
- catalog: agents=4 presets=5 copy=backlog
- agentqa: answer_events=122 references=0 saved_citations=0 citation_blocked=true
- history: native_agentqa output listed
```

History/citation smoke after the rebuilt runtime:

```text
WeKnora native history/citation unification
- decision: PASS
- evidence_type: live_api
- knowledge_chat: saved_citations=2 traceable=2 locator=located
- agentqa: saved_citations=0 traceable=0 citation_blocked=true
- history: filters distinguish WeKnora and citation_blocked outputs
```

The rebuilt runtime still emits zero traceable AgentQA references for the
current live workflow. Knowledge-chat citations continue to save and locate in
the same PA environment, so this is not a general PA citation persistence
failure.

## Coverage Impact

`AgentQA/custom Agent` remains `live-partial`.

Coverage remains:

```text
11.25 / 15 = 75.0%
```

No score is added from a deployed patch that still produces
`references=0`, `saved_citations=0`, and `citation_blocked=true` in the current
live AgentQA workflow.

## Required Next Step

The next AgentQA unblock must inspect why the live Agent path still does not
produce traceable references after the structured propagation patch is deployed.
Likely follow-up checks are whether the selected live Agent invokes
`knowledge_search`, whether its tool result contains structured
`Data["results"]`, and whether the runtime path that emits final Agent events
retains `AgentState.KnowledgeRefs`.

Only a current live run with `references > 0`, `saved_citations > 0`,
`citation_blocked=false`, and locatable history citations may promote
AgentQA/custom Agent to `live-full`.
