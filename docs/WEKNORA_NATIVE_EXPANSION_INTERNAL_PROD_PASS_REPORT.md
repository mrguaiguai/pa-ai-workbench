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
11.25 / 15 = 75.0%
```

The minimum internal production target is:

```text
12.00 / 15 = 80.0%
```

The blocker is real and should not be hidden: the current runtime has
insufficient eligible coverage for a final internal production PASS. The
remaining gap is primarily in configured connector workflow coverage and
traceable native AgentQA citation evidence. This report therefore records
`WNX-P3-02` as blocked instead of claiming an unverified final PASS.

## Current Evidence Summary

| Area | Evidence class | Current decision |
| --- | --- | --- |
| Native architecture and coverage model | audit/map | Complete; coverage scoring and boundaries are explicit. |
| Native client/status/acceptance harness | checker execution evidence, live API evidence | Complete; status center and guardrails are present. |
| Deployment readiness | live service/status evidence | Complete for local internal production recovery. |
| KB/document/chunk lifecycle | live API/browser evidence | Complete for the scoped PA product contract. |
| RAG and knowledge-chat | live API/browser evidence | Complete with traceable native citations where returned by WeKnora. |
| AgentQA/custom Agent | partial evidence | Native answer/history workflow is live, but citation references were not traceable in the live run. |
| Native Wiki | live API/browser evidence | Complete for scoped read/search/workflow and confirmation-gated mutations. |
| MCP, web search, vector store, model/config | partial evidence | Safe live readiness is visible; credential-heavy admin/test workflows remain backlog. |
| Data source connectors | partial evidence and backlog evidence | Safe connector type/list visibility is live, but no configured connector exists for resources/validate/sync/log PASS. |
| FAQ/tags/favorites/skills | partial evidence and backlog evidence | Tags, favorites, and skills visibility are live-partial; FAQ and mutations remain blocked/backlog. |
| Product browser matrix | live browser evidence | Complete across seven routed views on desktop and mobile. |

## Coverage Computation

The current score comes from the committed coverage ledger:

```text
live-full groups: system/deployment, workspace/KB, document lifecycle,
chunk management, knowledge-search/RAG, knowledge-chat/session chat,
Native Wiki, history/citation/product shell

live-partial groups: AgentQA/custom Agent, MCP, web search, vector store,
model/embedding/rerank/parser, FAQ/tags/favorites/skills

read-only groups: data sources/connectors

score: 11.25 / 15 = 75.0%
target: 12.00 / 15 = 80.0%
```

The ledger target plan expected two moves before final internal production:

- AgentQA/custom Agent from `live-partial` to `live-full`, worth `+0.5`.
- Data sources/connectors from `read-only` to `live-partial`, worth `+0.25`.

The current WNX evidence does not justify both moves:

- AgentQA/custom Agent remains `live-partial` because native AgentQA did not
  emit traceable references in the live run, so PA correctly recorded citation
  blocking instead of fabricating citations.
- Data sources/connectors moved only to `read-only` in the current live runtime
  because connector types were available but configured data sources were `0`.
  Resources, validation, sync, pause, resume, and sync-log workflow PASS still
  require a safe configured connector and confirmation/audit handling.

## Live Status Refresh

The current acceptance harness was run with a temporary PA backend and live
native status center validation:

```text
WeKnora native expansion acceptance check passed
- reports checked: 18
- completed prerequisite tasks: 19
- coverage current: 11.25/15 = 75.0%
- coverage target: 12.00/15 = 80.0%
- stage in progress: True
- browser hooks: desktop/mobile capability center report present
- live status center: live_api groups=15 live=5 partial=9 blocked=0 backlog=1
```

This confirms the guardrails and live status center still work, but it does not
close the coverage gap.

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

- AgentQA/custom Agent answer/history without traceable native citations;
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
| Coverage below target | `75.0%`, target `80.0%` | Complete a real score-moving task or explicitly revise the target with governance approval. |
| AgentQA citation traceability | Native AgentQA answer/history is live but references are not traceable | Validate native reference shape or keep PA fail-closed citation blocker. |
| Data source connector workflow | Connector catalog/list is live; configured data sources are `0` | Add a sanitized configured connector smoke or mark the workflow outside this internal production cut. |

## Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Inflating read-only readiness into workflow PASS | Would overstate internal production readiness | Keep ledger at `read-only` or `live-partial` only when validated by live workflow evidence. |
| Treating AgentQA answer text as citation evidence | Would break PA citation contract | Keep `citation_blocked` visible until native references are traceable. |
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
