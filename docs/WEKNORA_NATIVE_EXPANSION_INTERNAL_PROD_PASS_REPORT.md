# WeKnora Native Expansion Internal Production Report

Date: 2026-06-23

Task: `WNX-P3-02`

Branch: `weknora-first-mvp`

Decision: `BLOCKED`

Evidence type: blocked evidence, checker execution evidence, live API evidence,
live browser evidence, live API/browser evidence, live service/status evidence,
audit/map, partial evidence, backlog evidence.

## Executive Decision

The Native Expansion internal production stage is not ready for final PASS.

Current verified coverage is:

```text
11.75 / 15 = 78.3%
```

The minimum internal production target is:

```text
12.00 / 15 = 80.0%
```

The blocker is real and should not be hidden: the current runtime has
insufficient eligible coverage for a final internal production PASS. The
remaining gap is primarily in configured connector workflow coverage and
no longer in traceable native AgentQA citation evidence. This report therefore records
`WNX-P3-02` as blocked instead of claiming an unverified final PASS.

## Current Evidence Summary

| Area | Evidence class | Current decision |
| --- | --- | --- |
| Native architecture and coverage model | audit/map | Complete; coverage scoring and boundaries are explicit. |
| Native client/status/acceptance harness | checker execution evidence, live API evidence | Complete; status center and guardrails are present. |
| Deployment readiness | live service/status evidence | Complete for local internal production recovery. |
| KB/document/chunk lifecycle | live API/browser evidence | Complete for the scoped PA product contract. |
| RAG and knowledge-chat | live API/browser evidence | Complete with traceable native citations where returned by WeKnora. |
| AgentQA/custom Agent | live API evidence | Native answer/history workflow and traceable Wiki citations are live after `WNX-P3-08`; Agent copy/update/delete remain backlog. |
| Native Wiki | live API/browser evidence | Complete for scoped read/search/workflow and confirmation-gated mutations. |
| MCP, web search, vector store, model/config | partial evidence | Safe live readiness is visible; credential-heavy admin/test workflows remain backlog. |
| Data source connectors | partial evidence, blocked evidence, and backlog evidence | Safe connector type/list visibility is live, but `WNX-P3-05` revalidated that no configured connector exists for resources/validate/sync/log PASS. |
| FAQ/tags/favorites/skills | partial evidence and backlog evidence | Tags, favorites, and skills visibility are live-partial; FAQ and mutations remain blocked/backlog. |
| Product browser matrix | live browser evidence | Complete across seven routed views on desktop and mobile. |

## Coverage Computation

The current score comes from the committed coverage ledger:

```text
live-full groups: system/deployment, workspace/KB, document lifecycle,
chunk management, knowledge-search/RAG, knowledge-chat/session chat,
AgentQA/custom Agent, Native Wiki, history/citation/product shell

live-partial groups: MCP, web search, vector store, model/embedding/rerank/parser,
FAQ/tags/favorites/skills

read-only groups: data sources/connectors

score: 11.75 / 15 = 78.3%
target: 12.00 / 15 = 80.0%
```

The ledger target plan expected two moves before final internal production:

- AgentQA/custom Agent from `live-partial` to `live-full`, worth `+0.5`.
- Data sources/connectors from `read-only` to `live-partial`, worth `+0.25`.

The current WNX evidence justifies the AgentQA move but not the connector move:

- AgentQA/custom Agent is now `live-full`. `WNX-P3-08` traced the live selected
  Agent path to Wiki tools, added structured Wiki references, and validated
  `references=12`, `saved_citations=12`, `citation_blocked=false`, plus AgentQA
  history citations with locator success.
- Data sources/connectors moved only to `read-only` in the current live runtime
  because connector types were available but configured data sources were `0`.
  `WNX-P3-05` revalidated `connector_types.count=12`,
  `data_sources.count=0`, and `credentials_configured=0`. Resources,
  validation, sync, pause, resume, and sync-log workflow PASS still require a
  safe configured connector and confirmation/audit handling.

## AgentQA Traceability Refresh

`WNX-P3-04` audited the native AgentQA references path and the PA AgentQA
parser/citation path, then reran live AgentQA and history/citation smokes.

Current live evidence:

```text
agentqa: answer_events=157 references=0 saved_citations=0 citation_blocked=true
knowledge_chat: saved_citations=2 traceable=2 locator=located
agentqa history: saved_citations=0 traceable=0 citation_blocked=true
```

This confirms the AgentQA blocker is not a general PA citation persistence
failure. Native knowledge-chat can still persist locatable citations in the
same environment. AgentQA remains blocked because traceable native references
are absent.

## AgentQA Reference Propagation Patch Refresh

`WNX-P3-06` drafted a narrow local native patch that propagates structured
`knowledge_search` results into standard native `references` events instead of
parsing Agent answer text or free-form tool output. `WNX-P3-07` then formatted
and focused-tested that patch with Docker Go tooling, rebuilt
`wechatopenai/weknora-app:latest`, and recreated only the `WeKnora-app`
container.

Patch draft files outside the PA git repository:

```text
internal/agent/engine.go
internal/agent/act.go
internal/agent/tools/knowledge_search.go
internal/agent/act_references_test.go
```

The patch still cannot move coverage because the rebuilt live AgentQA workflow
does not emit traceable references.

Current live validation after the rebuilt runtime reports:

```text
agentqa: answer_events=122 references=0 saved_citations=0 citation_blocked=true
knowledge_chat: saved_citations=2 traceable=2 locator=located
agentqa history: saved_citations=0 traceable=0 citation_blocked=true
```

At the `WNX-P3-07` checkpoint, AgentQA/custom Agent still remained
`live-partial`. That conclusion is superseded by the `WNX-P3-08` Wiki reference
fix below.

## AgentQA Wiki Reference Live Fix

`WNX-P3-08` found that the live selected AgentQA path uses Wiki tools rather
than `knowledge_search`. Native `wiki_search` and `wiki_read_page` now expose
structured Wiki page references, the stream conversion preserves
`source_type=wiki_page`, and PA history/status classify traceable WeKnora
citations correctly.

Current live validation after the Wiki reference fix reports:

```text
agentqa: answer_events=167 references=12 saved_citations=12 citation_blocked=false
knowledge_chat: saved_citations=2 traceable=2 locator=located
agentqa history: saved_citations=15 traceable=15 citation_blocked=false
```

AgentQA/custom Agent is now `live-full`; total coverage is
`11.75 / 15 = 78.3%`.

## Data Source Connector Refresh

`WNX-P3-05` audited the native data source connector routes and PA masked data
source BFF path, then reran the live data source management smoke with browser
validation.

Current live evidence:

```text
coverage_state: read-only
connector_types: status=live count=12
data_sources: status=live count=0 credentials_configured=0
connector_read: backlog detail=not_configured
resources: backlog
validation: backlog
sync_control: overview=backlog blocked_path=backlog confirmed_path=not_requested
```

This confirms the Data sources/connectors blocker is not connector catalog
visibility. The blocker is the absence of a safe configured connector in the
current runtime.

## Live Status Refresh

The current acceptance harness was run with a temporary PA backend and live
native status center validation:

```text
WeKnora native expansion acceptance check passed
- reports checked: 28
- completed prerequisite tasks: 24
- coverage current: 11.75/15 = 78.3%
- coverage target: 12.00/15 = 80.0%
- stage in progress: False
- browser hooks: desktop/mobile capability center report present
- live status center: live_api groups=15 live=6 partial=8 blocked=0 backlog=1
```

This still does not close the coverage gap because Data sources/connectors
remains `read-only`.

Current final blocked marker:

```text
- coverage current: 11.75/15 = 78.3%
- coverage target: 12.00/15 = 80.0%
```

## Browser Evidence

`WNX-P3-01` supplied current live browser evidence across the PA product shell:

```text
WeKnora native product workflow browser matrix
- decision: PASS
- evidence_type: live_browser_evidence
- api: native_status_schema=wnx-p0-02 groups=15
- browser: routes=7 viewport_checks=14
- desktop: pass=7 overflow=0 visible_overlap=0
- mobile: pass=7 overflow=0 visible_overlap=0
```

The browser matrix proves product workflow coherence. It does not upgrade
read-only or partial native capability groups into final coverage PASS.

## Evidence Boundaries

Live evidence used:

- live PA BFF/native status center responses;
- live PA backend/frontend browser matrix;
- live API/browser reports for KB, document, chunk, RAG, knowledge-chat,
  AgentQA, Wiki, history/citation, model/config, MCP, web search, vector store,
  data source connectors, and organization surfaces;
- live service/status deployment readiness.

Audit/map evidence used:

- architecture report;
- coverage ledger and scoring model;
- acceptance harness and report-safety guardrails.

Partial evidence used:

- platform management surfaces that safely expose readiness but not credential
  or mutation workflows;
- organization surfaces with FAQ blocked and mutations deferred.

Backlog evidence used:

- credential-heavy MCP/web-search/vector-store/model/data-source admin flows;
- connector resources/validate/sync/log workflows without a configured safe
  connector;
- FAQ/tag/favorite/skill mutations;
- global Wiki maintenance mutations without explicit operator confirmation.

Mock evidence, fixture-only evidence, cached evidence, old reports, static UI,
and hidden fallback are not used as final PASS evidence.

## Blockers

| Blocker | Current state | Required next step |
| --- | --- | --- |
| Coverage below target | `78.3%`, target `80.0%` | Complete a real Data sources/connectors score-moving task or explicitly revise the target with governance approval. |
| Data source connector workflow | `WNX-P3-09` revalidated connector catalog `count=12`, but configured data sources are still `0` and implemented connectors require real external credentials | Configure a safe native Feishu/Notion/Yuque data source outside Codex output, then rerun sanitized connector detail/resources/validate/sync/log smoke. |

## Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Inflating read-only readiness into workflow PASS | Would overstate internal production readiness | Keep ledger at `read-only` or `live-partial` only when validated by live workflow evidence. |
| Treating AgentQA answer text as citation evidence | Would break PA citation contract | `WNX-P3-08` passes through structured Wiki references only; keep this rule for future Agent paths. |
| Running credential-heavy admin tests without confirmation | Could leak or mutate provider configuration | Keep these surfaces backlog until explicit confirmation, masking, and audit trail exist. |
| Final report filename implies PASS | Could mislead future agents | This report states `Decision: BLOCKED` and the spec row is marked `[!]`. |

## Validation

Commands run for this task:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py --start-pa-api
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py --self-test
git diff --check
rg sensitive-value scan for this report and the spec update
rg unsafe PASS phrase scan for this report and the spec update
```

Sensitive-value scans covered this report and the spec update before commit.

## Final Status

`WNX-P3-02` is blocked with current evidence.

The stage should not be called internal production PASS until coverage reaches
at least `12.00 / 15 = 80.0%` through real current-run evidence, or until the
target is explicitly changed by a governance task.
