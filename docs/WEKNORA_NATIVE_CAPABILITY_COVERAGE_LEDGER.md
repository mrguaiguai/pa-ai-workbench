# WeKnora Native Capability Coverage Ledger

> Task: `WNX-0-03`
>
> Date: 2026-06-22
>
> Evidence type: audit/map. This ledger establishes the baseline and scoring
> method for the Native Expansion stage; it does not create new live capability
> PASS evidence.

## Purpose

This ledger makes the Native Expansion 80% coverage target executable. It
enumerates every eligible WeKnora native capability group, assigns the current
baseline state, records the target state, links the evidence source, and maps
the next `WNX-*` task that should move the group.

Important evidence boundary:

- Current state is based on committed branch evidence from the prior
  WeKnora-first stage, the native expansion spec, and the architecture
  blueprint.
- Prior `WF-*` reports can justify the starting baseline, but future internal
  production PASS in `WNX-P3-02` must refresh live evidence through current
  `WNX-*` validation.
- No score is granted from mock evidence, fixture-only evidence, static UI,
  cached browser state, hidden fallback, or unverified inference.

## Scoring Model

| State | Score | Meaning |
| --- | ---: | --- |
| `live-full` | 1.0 | Real PA path calls real WeKnora native capability and satisfies the PA contract, including history/citation/status when applicable. |
| `live-partial` | 0.5 | Real native call works, but the PA contract is incomplete, such as missing citation, incomplete mutation controls, incomplete history, or partial workflow coverage. |
| `read-only` | 0.25 | PA can safely inspect native status/list/catalog, but cannot execute the user workflow. |
| `blocked` | 0 | A real API/config/runtime/safety gap prevents completion. |
| `backlog` | 0 | Deferred by stage scope or risk. |
| `unsafe-for-pa` | 0 | Not suitable for PA exposure without a separate safety design. |

Formula:

```text
coverage = sum(current_score) / count(eligible_capability_groups)
target_coverage = sum(target_score) / count(eligible_capability_groups)
```

Eligible capability groups: `15`.

Current score:

```text
9.75 / 15 = 65.0%
```

Minimum internal production target:

```text
12.00 / 15 = 80.0%
```

The target deliberately reaches exactly the stage threshold without forcing
credential-heavy platform admin surfaces to become `live-full`. MCP, web
search, vector store, model/config/parser, data source, and organization
features can count as `live-partial` when PA exposes safe live readiness or
safe limited workflows without leaking secrets or rebuilding WeKnora admin.

## Current Coverage Ledger

| Capability group | Current state | Score | Target state | Target score | Current evidence source | Validation method | Risk / blocker | Next action |
| --- | --- | ---: | --- | ---: | --- | --- | --- | --- |
| System health/status/deployment | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md`; `docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_REPORT.md`; `/health`, `/api/status`, `/api/model/status`, `/api/native/status`, and temporary frontend service were validated live in `WNX-P0-05`. | `WNX-P0-05` live service/status smoke and runbook validation. | Local internal production recovery is validated; cloud deployment remains outside this stage, and deeper parser management remains `WNX-P2-01`. | `WNX-P3-02`, `WNX-P2-01` |
| Workspace/knowledge-base management | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_KB_SELECTION_MAPPING_REPORT.md`; `docs/WEKNORA_NATIVE_KB_MANAGEMENT_LIVE_REPORT.md`; WNX-P1-01 validated live KB list/read, active PA DB selection snapshot, upload target propagation, safe tag visibility, and Library browser selector. | `WNX-P1-01` live API/browser smoke with temporary backend/frontend and Chrome DOM validation. | Destructive KB create/update/delete and pin/tag write flows remain backlog until confirmation and audit trail exist. | `WNX-P3-02` |
| Document lifecycle | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_DOCUMENT_RAG_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_DOCUMENT_LIFECYCLE_LIVE_REPORT.md`; WNX-P1-02 validated live file upload/index/chunks, URL ingestion, manual ingestion, spans, preview/download, reparse, delete submission, safe cancel control, and Library browser workflow. | `WNX-P1-02` live API/browser smoke with temporary backend/frontend, temporary DB, and sanitized output. | Native delete is asynchronous, cancel only applies to active processing, and destructive chunk mutation remains separate `WNX-P1-03` scope. | `WNX-P1-03`, `WNX-P3-02` |
| Chunk management | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_DOCUMENT_RAG_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_CHUNK_MANAGEMENT_LIVE_REPORT.md`; WNX-P1-03 validated native chunk list/by-id, PA-scoped chunk detail, enable/disable, delete with confirmation, audit events, and Library browser chunk workflow. | `WNX-P1-03` live API/browser smoke with temporary backend/frontend, temporary DB/uploads, and sanitized output. | Content rewrite remains backlog until re-embedding safety is proven; generated-question delete needs generated-question test data; search-by-chunk native route was not found. Chunk status cannot be treated as answer evidence. | `WNX-P1-04`, `WNX-P3-02` |
| Knowledge-search/RAG | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_RAG_DEBUG_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_RAG_KNOWLEDGE_CHAT_LIVE_REPORT.md`; PA RAG debug called native search and returned `source=weknora_api`, `source_type=document_chunk`, `evidence_id`, rank, trace, native ids, and current-run evidence. | Current-run live RAG debug smoke with source scope and citation checks. | Search path is live-full for RAG debug; advanced ranking UI remains backlog beyond internal use. | `WNX-P3-02` |
| Knowledge-chat/session chat | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_NATIVE_RAG_KNOWLEDGE_CHAT_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_HISTORY_CITATION_UNIFICATION_LIVE_REPORT.md`; WNX-P1-04 validated native `/api/v1/knowledge-chat`, PA conversation/history/output persistence, native references saved as citations, and current-run guard; WNX-P1-07 revalidated locatable history citations. | `WNX-P1-04` and `WNX-P1-07` live API/browser smokes with temporary backend/frontend and sanitized output. | Citation PASS depends on native `references` events containing traceable document or Wiki identity; current PA history now exposes traceable counts and locator status. | `WNX-P3-02` |
| AgentQA/custom Agent | `live-partial` | 0.5 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_AGENTQA_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_AGENTQA_CUSTOM_AGENT_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_HISTORY_CITATION_UNIFICATION_LIVE_REPORT.md`; WNX-P1-05 validated native custom Agent catalog, presets, placeholders, suggested questions, PA Analysis browser workflow, and native AgentQA output/history persistence; WNX-P1-07 validates visible `citation_blocked` fail-closed handling. | `WNX-P1-05` and `WNX-P1-07` live API/browser workflows. Citation PASS requires traceable native references. | AgentQA answer/history and custom Agent picker are live; citation references were absent in the live run, so the capability remains partial; Agent copy/update/delete remain backlog until ownership/confirmation/audit design exists. | `WNX-P3-02` |
| Native Wiki | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md`; `docs/WEKNORA_NATIVE_WIKI_WORKFLOW_LIVE_REPORT.md`; `docs/WEKNORA_NATIVE_HISTORY_CITATION_UNIFICATION_LIVE_REPORT.md`; WNX-P1-06 validated native Wiki pages/search/read/index/log/graph/stats/lint/issues, safe create/update/delete on a temporary page, and Wiki browser workflow; WNX-P1-07 normalizes Wiki citation deep links to `#/wiki?slug=...`. | `WNX-P1-06` live API/browser smoke with confirmation-gated native mutations; `WNX-P1-07` citation locator validation. | Global rebuild-links/auto-fix and issue-status mutation require operator confirmation and must not run from status-only refreshes. | `WNX-P3-02` |
| MCP | `read-only` | 0.25 | `live-partial` | 0.5 | `docs/WEKNORA_FIRST_MCP_VISIBILITY_REPORT.md`; PA read native MCP service list safely; tools/resources/approval/mutations backlog. | Live MCP list/read/test where configured, browser status, sensitive scan. | Credential forms, tool execution, approval mutation, and service CRUD are unsafe without explicit approval model. | `WNX-P2-02` |
| Web search | `read-only` | 0.25 | `live-partial` | 0.5 | `docs/WEKNORA_FIRST_WEB_SEARCH_VISIBILITY_REPORT.md`; PA read provider catalog/configured providers and marked AgentQA dependency optional/unconfigured. | Live provider readiness/test where configured and AgentQA dependency validation. | Provider CRUD, credential handling, raw search debugging, and PA-owned web search orchestration remain backlog. | `WNX-P2-03` |
| Vector store | `read-only` | 0.25 | `live-partial` | 0.5 | `docs/WEKNORA_FIRST_VECTOR_STORE_VISIBILITY_REPORT.md`; PA read vector-store types/list, KB binding, and embedding readiness without raw config. | Live vector-store readiness/test where safe, KB binding check, sensitive scan. | CRUD, connection tests, raw config display, KB rebind mutation, and PA-owned vector administration remain backlog. | `WNX-P2-04` |
| Model/embedding/rerank/parser | `live-partial` | 0.5 | `live-partial` | 0.5 | `docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md`; `docs/WEKNORA_FIRST_VECTOR_STORE_VISIBILITY_REPORT.md`; prior status showed non-mock chat/embedding and live embedding posture. | Masked model/embedding/rerank/parser status API and safe remote checks. | Chat/embedding posture exists; model catalog, rerank, parser engine, remote test calls, and sanitized provider status are not unified. | `WNX-P2-01` |
| Data sources/connectors | `backlog` | 0 | `live-partial` | 0.5 | `docs/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md`; native data source routes identified for future safe status/sync slices. | Live connector type/status/resources/sync smoke with sanitized output. | Credential-heavy connector setup and sync logs may expose secrets; start with read-only or safe validate/resources. | `WNX-P2-05` |
| FAQ/tags/favorites/skills | `backlog` | 0 | `live-partial` | 0.5 | `docs/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md`; native FAQ/tags/favorites/skills route families identified. | Live API smoke for at least one organization primitive plus browser workflow. | Useful workbench polish, but not yet integrated into PA UX; avoid inventing a parallel taxonomy. | `WNX-P2-06` |
| History/citation/product shell | `live-full` | 1.0 | `live-full` | 1.0 | `docs/WEKNORA_FIRST_CITATION_CONTRACT.md`; `docs/WEKNORA_FIRST_FRONTEND_BROWSER_ACCEPTANCE_REPORT.md`; `docs/WEKNORA_NATIVE_HISTORY_CITATION_UNIFICATION_LIVE_REPORT.md`; PA pages, citation contract, traceable counts, citation locators, and visible native citation blockers are live. | `WNX-P1-07` live API/browser validation across native knowledge-chat history, citation locator, AgentQA citation blocker, History filters, and browser DOM. | AgentQA citation remains blocked at the native reference level, but PA now fails closed visibly instead of fabricating citations. Advanced history analytics remain backlog. | `WNX-P3-01`, `WNX-P3-02` |

## Target Coverage Plan

The minimum target plan reaches 80% by completing these state moves:

| Move | Groups | Score gain |
| --- | --- | ---: |
| `live-partial` to `live-full` | AgentQA/custom Agent | +0.5 |
| `read-only` to `live-partial` | MCP, Web search, Vector store | +0.75 |
| `backlog` to `live-partial` | Data sources/connectors, FAQ/tags/favorites/skills | +1.0 |
| Keep `live-partial` target | Model/embedding/rerank/parser | +0 |

Planned target score:

```text
9.75 current + 2.25 planned gain = 12.00 / 15 = 80.0%
```

Stretch target:

- Promote MCP, web search, vector store, and model/config/parser from
  `live-partial` to `live-full` only when safe mutation/test workflows exist
  without secret leakage.
- Promote data sources and FAQ/tags/favorites/skills to `live-full` only after
  browser workflows and PA history/status integration are validated.

## Evidence Freshness Rules

Future tasks must update this ledger when they change a capability state:

1. Add or update the evidence report link.
2. Keep live evidence, fixture evidence, mock evidence, cached evidence,
   partial evidence, blocked evidence, and backlog evidence separate.
3. Recompute the score.
4. Never upgrade a state from report text alone if the relevant task requires
   live API, browser, or service validation.
5. Treat read-only visibility as at most `read-only` unless PA can execute a
   real user workflow.
6. Treat status/config/provider readiness as status, not citation evidence.
7. Treat AgentQA/custom Agent answers without traceable references as
   `live-partial` at most when citation is part of the PA contract.

## Blocked And Backlog Baseline

| Area | Baseline decision |
| --- | --- |
| AgentQA citation mapping | Blocked until native AgentQA emits traceable references or PA receives a documented native citation shape. |
| Native Wiki global maintenance | Operator-confirmed only; rebuild-links, auto-fix, and issue-status mutation must not run from status-only refreshes. |
| MCP execution and credentials | Backlog/unsafe until approval and secret-handling model is explicit. |
| Web search provider credentials and raw tests | Backlog until a secure masked credential flow is explicitly scoped. |
| Vector-store CRUD/test/raw config | Backlog until PA can avoid raw DSN/config leakage and avoid conflicting with WeKnora admin ownership. |
| Data source credentials and sync logs | Backlog until sanitized validate/resources/sync output is proven safe. |
| General PA-native Agent/RAG/Wiki expansion | Backlog by stage policy when WeKnora has a native path. |

## Next Ledger Update Points

- `WNX-P0-01`: update adapter-related risks if shared client changes evidence
  normalization or safe status shape.
- `WNX-P0-02`: update system, model/config, MCP, web search, vector store,
  data source, FAQ/tag/favorite/skill status baselines from the unified status
  center.
- `WNX-P0-04`: add checker evidence and any computed score validation.
- `WNX-P0-05`: upgrades system health/status/deployment to `live-full` from
  live service/status evidence and internal recovery runbook validation.
- `WNX-P1-01`: upgrades workspace/knowledge-base management to `live-full`
  after live API/browser selection workflow evidence.
- `WNX-P1-*`: upgrade workflow groups only after live API/browser evidence.
- `WNX-P2-*`: upgrade platform groups only after sanitized live status or safe
  workflow validation.
- `WNX-P3-02`: recompute final score from current WNX evidence, not just prior
  WF reports.

## WNX-P0-04 Harness Validation

`WNX-P0-04` adds `backend/scripts/check_weknora_native_expansion_acceptance.py`
and `docs/WEKNORA_NATIVE_EXPANSION_ACCEPTANCE_HARNESS_REPORT.md`.

The harness validates the ledger math and stage evidence boundaries:

- the checker parses the current ledger score; after `WNX-P1-07` this is
  `9.75 / 15 = 65.0%`;
- target score remains `12.00 / 15 = 80.0%`;
- current score below target is allowed only because the WNX stage is still in
  progress;
- the checker fails unsafe mock, fixture-only, cached, static UI, or
  secret-shaped PASS claims;
- browser hooks are currently represented by the WNX-P0-03 desktop/mobile
  capability center report;
- optional live API validation checks `/api/native/status` for 15 masked groups
  without printing raw payloads.

No capability group score changes from this harness alone. Future `WNX-P1-*`
and `WNX-P2-*` tasks must still supply their own live API/browser evidence
before this ledger can move any group toward the 80% target.

## PASS Boundary For This Ledger

`WNX-0-03` is complete when this ledger:

- lists all eligible capability groups from the spec;
- shows current state, target state, score, evidence source, risk, and next
  action for each group;
- computes the current baseline and the 80% target;
- avoids inflating read-only visibility into live-full capability; and
- passes diff, keyword, and sensitive-value checks.
