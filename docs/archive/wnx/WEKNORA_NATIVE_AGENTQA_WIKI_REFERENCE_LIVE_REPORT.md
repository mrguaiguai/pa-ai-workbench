# WeKnora Native AgentQA Wiki Reference Live Report

Date: 2026-06-23

Task: `WNX-P3-08`

Branch: `weknora-first-mvp`

Decision: `PASS`

Evidence type: native Go test evidence, Docker runtime deployment evidence, live
API evidence.

## Scope

`WNX-P3-08` resolves the AgentQA citation blocker for the currently selected
native custom Agent path. The live catalog selects `builtin-wiki-researcher`,
which uses Wiki tools rather than `knowledge_search`, so `WNX-P3-06` and
`WNX-P3-07` could not emit references for the default AgentQA workflow.

This task keeps the citation contract strict:

- no Agent answer text is accepted as citation evidence;
- no free-form tool output XML is parsed as evidence;
- only structured native tool result data is converted into references;
- PA saves citations only when source identity is traceable and locatable.

## Root Cause

The deployed `WNX-P3-07` patch only extracted references from
`knowledge_search` tool results. The current live AgentQA workflow selected
`builtin-wiki-researcher`, whose allowed and observed tools are Wiki tools.

Sanitized live tool-path probe:

```text
selected_agent_id=builtin-wiki-researcher
allowed_tools=wiki_search,wiki_read_page,wiki_read_source_doc,wiki_flag_issue
tool_names=wiki_search,wiki_read_page,final_answer
references=0 before the wiki reference patch
```

The missing reference path was therefore native Wiki tool result propagation,
not PA answer-text parsing.

## Native Patch

Native source files changed in the outer WeKnora source tree:

```text
internal/agent/tools/wiki_tools.go
internal/agent/act.go
internal/agent/act_references_test.go
internal/types/search.go
internal/handler/session/agent_stream_handler.go
internal/handler/session/helpers.go
```

Patch shape:

- `wiki_search` and `wiki_read_page` now expose structured `wiki_pages` data in
  `ToolResult.Data`.
- Agent reference extraction now supports `wiki_search` and `wiki_read_page`.
- Wiki references serialize `source_type=wiki_page`, `wiki_page_id`, and
  `wiki_page_slug`.
- The session stream conversion preserves those fields and metadata.
- Native reference extraction tests cover both document search references and
  Wiki page references.

This patch does not parse answer text or free-form XML output.

## PA Patch

PA files changed:

```text
backend/app/services/history_service.py
backend/app/services/native_status_service.py
```

PA history classification now treats traceable non-mock citations as WeKnora
evidence when the source label varies, while still requiring locator-grade
citation metadata. The native status center now reports AgentQA/custom Agent as
live after the current-run citation evidence passed.

## Validation

Focused native tests:

```text
go test ./internal/agent -run 'TestExtractKnowledgeReferencesFromToolResult|TestExtractWikiReferencesFromToolResult|TestAppendUniqueKnowledgeReferences'
ok github.com/Tencent/WeKnora/internal/agent
```

Session handler compile/test:

```text
go test ./internal/handler/session
ok github.com/Tencent/WeKnora/internal/handler/session
```

Production runtime deployment:

```text
docker compose -f docker-compose.yml build app
docker compose -f docker-compose.yml up -d --no-deps --force-recreate app
curl http://127.0.0.1:8080/health -> {"status":"ok"}
```

Sanitized live reference shape after deployment:

```text
response_type=references
source_type=wiki_page
wiki_page_id_present=true
wiki_page_slug_present=true
metadata includes source_type and wiki slug fields
```

Live AgentQA workflow smoke:

```text
WeKnora native AgentQA/custom Agent workflow
- decision: PASS
- evidence_type: live_api
- catalog: agents=4 presets=5 copy=backlog
- agentqa: answer_events=167 references=12 saved_citations=12 citation_blocked=false
- history: native_agentqa output listed
```

Live history/citation smoke:

```text
WeKnora native history/citation unification
- decision: PASS
- evidence_type: live_api
- knowledge_chat: saved_citations=2 traceable=2 locator=located
- agentqa: saved_citations=15 traceable=15 citation_blocked=false
- history: filters distinguish WeKnora and citation_blocked outputs
```

## Coverage Impact

`AgentQA/custom Agent` moves from `live-partial` to `live-full`.

Coverage moves from:

```text
11.25 / 15 = 75.0%
```

to:

```text
11.75 / 15 = 78.3%
```

The stage still does not reach the final internal production target:

```text
12.00 / 15 = 80.0%
```

The remaining score-moving blocker is Data sources/connectors, which still
requires a safe configured connector workflow to move from `read-only` to
`live-partial`.

## Residual Risk

The native source tree is outside the nested PA git repository, so the PA
commit records the live evidence and PA-side status/history fixes, while the
native source edits remain in the outer workspace source tree and rebuilt local
runtime. A future native-source repository handoff should carry these exact
native file changes before broader deployment.
