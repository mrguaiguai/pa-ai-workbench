# WeKnora-First Citation Contract

> Task: `WF-P0-05`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: audit/map plus focused smoke. The prior P0 live reports remain
> supporting context for native document and RAG behavior; this task did not
> change live retrieval or frontend rendering paths.

## Scope And Evidence Boundary

`WF-P0-05` preserves PA's citation/evidence contract while PA consumes
WeKnora native document, chunk, search, and Wiki paths. PA owns the contract,
history records, report safety, and locator behavior. WeKnora owns native
ingestion, chunking, retrieval, Wiki storage, and future native Agent/tool
capabilities.

This document is not fixture-only PASS. The PASS claim is limited to contract
definition and a current focused smoke that validates PA mapping, persistence,
locator fields, and fail closed behavior. Live native capability evidence is
kept in the `WF-P0-02` and `WF-P0-03` reports and is not re-invented here.

Unsafe evidence remains rejected for final PASS:

| Evidence category | Contract decision |
| --- | --- |
| live | Required when code changes touch live PA + WeKnora behavior. Prior P0 live reports are supporting context only for this audit/smoke slice. |
| fixture-only | Allowed only for focused regression checks; not final capability PASS by itself. |
| mock | Allowed only for dev/test paths; mock evidence is not PASS. |
| cached | Old reports and old ids are not PASS unless the live path is rerun and labelled current. |
| partial | Partial native citation support must be labelled partial or blocked, not completed. |
| blocked | Missing native ids or unsupported response shapes block citation PASS. |
| backlog | Deferred native areas stay backlog until a live mapping exists. |

## Sources Audited

Existing PA contract surfaces audited:

- `knowledge_engine/schemas.py`
- `knowledge_engine/evidence.py`
- `knowledge_engine/citations/schemas.py`
- `knowledge_engine/citations/builder.py`
- `knowledge_engine/backends/weknora_api_backend.py`
- `agent/schemas.py`
- `agent/tools/citation_checker.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/generation_service.py`
- `backend/app/services/history_service.py`
- `backend/app/services/citation_locator_service.py`
- `backend/app/api/rag.py`
- `backend/app/api/citations.py`
- `backend/scripts/check_phase5_report_safety.py`
- `backend/scripts/smoke_weknora_citation_contract_m1.py`

Sprint mapping and evidence reports audited:

- `docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`
- `docs/WEKNORA_FIRST_DOCUMENT_RAG_LIVE_REPORT.md`
- `docs/WEKNORA_FIRST_RAG_DEBUG_LIVE_REPORT.md`
- `docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md`
- Phase 5 real reports for document, RAG, Wiki, knowledge QA, frontend, and
  final gate evidence style.

## Required Contract Fields

Every real non-mock citation or evidence item must keep these fields traceable:

| Field | Requirement | Reason |
| --- | --- | --- |
| `source` | Required. WeKnora native evidence uses `weknora_api`. | Lets history and reports separate real WeKnora evidence from mock or local fallback. |
| `source_type` | Required and normalized. Current PASS types are `document_chunk` and `wiki_page`. | Drives citation checks, history filters, and locator routing. |
| `evidence_id` | Required for real citations. It must come from native ids or deterministic PA mapping from native ids. | Prevents untraceable evidence in reports and history. |
| `chunk_id` | Required when `source_type=document_chunk`. | Locates document evidence and prevents whole-document-only claims. |
| `external_doc_id` or PA `document_id` | Required when `source_type=document_chunk`; WeKnora-native paths should prefer `external_doc_id`. | Links PA business records to native WeKnora knowledge ids. |
| `wiki_page_id` | Required when `source_type=wiki_page`. | Preserves Wiki citation identity across history and locator APIs. |
| `locator` fields | Required by source type: document citations need document/chunk fields; Wiki citations need page id and slug when available. | Allows `/api/citations/locate` to route to Library or Wiki without guessing. |
| `title` and `text` | Required for saved citations. | Keeps history and reports human-readable without exposing raw native payloads. |
| `score` / rank / trace metadata | Optional but preserved when native response provides it. | Supports debug trust without making unavailable scores look precise. |

PA must not invent fake `evidence_id`, `chunk_id`, `external_doc_id`, or
`wiki_page_id`. If the native response lacks the identifier needed for the
source type, the path must fail closed or be labelled blocked/partial.

## Per-Source Mapping Rules

| Source type | Native input | PA mapping | Required locator outcome | Status |
| --- | --- | --- | --- | --- |
| `document_chunk` | WeKnora search/chunk result with native result `id` or chunk id plus knowledge/document id. | `source=weknora_api`, `source_type=document_chunk`, `chunk_id=<native chunk id>`, `external_doc_id=<knowledge id>`, `evidence_id=document_chunk:<chunk_id>`. | Locate to `/library` when PA has the document record; otherwise report unavailable instead of guessing. | PASS for P0 document/RAG paths. |
| `wiki_page` | WeKnora Wiki page/search/read result with page id or stable slug. | `source=weknora_api`, `source_type=wiki_page`, `wiki_page_id=<native id or stable slug>`, `evidence_id=wiki_page:<wiki_page_id>`, metadata carries Wiki slug when available. | Locate to `/wiki` when PA has slug or a stored Wiki page; otherwise report unavailable instead of guessing. | PASS for current PA Wiki citation contract; richer native browse remains P1. |
| Native AgentQA/custom Agent | Native answer/citation stream or response. | Must map returned citations into the same PA fields before saving history. If returned citations lack traceable ids, PA must store an explicit blocker/warning rather than PASS. | History may save the answer, but citation PASS is blocked until ids and locator fields are proven live. | Backlog until `WF-P1-01`. |
| MCP / web search / vector store | Native read-only capability/status data or future tool outputs. | Do not treat provider/tool/status records as document or Wiki evidence. Add a source type only after a real id and locator policy exists. | Readiness can be shown as status; citation locator is blocked/backlog until a contract is defined. | Backlog by P2 scope. |

## Metadata Allowlist

The PA debug/report/browser surface must use an allowlist, not raw native
metadata dumps. Current allowed public metadata includes:

- Contract ids: `evidence_id`, `citation_source_type`, `source_type`.
- WeKnora ids and structure: `weknora_knowledge_base_id`,
  `weknora_knowledge_id`, `weknora_chunk_index`, `weknora_start_at`,
  `weknora_end_at`, `weknora_seq`, `weknora_match_type`,
  `weknora_chunk_type`, `weknora_parent_chunk_id`,
  `weknora_wiki_page_id`, `weknora_wiki_page_slug`.
- Retrieval diagnostics: `weknora_search_endpoint`, `weknora_search_native`,
  `weknora_native_rank`, `retrieval_debug_trace`, `retrieval_options`,
  `retrieval_rank`, `raw_retrieval_rank`, `score_display`,
  `score_display_mode`.
- Current-run and guard labels: `current_run_id`, `current_run_scope`,
  `current_run_isolated`, `source_scope`, `source_scope_warnings`,
  `distractor_guard_decision`, `distractor_guard_warnings`.
- Safe business labels: `business_area`, `document_type`, `slug`, `page_type`.

The allowlist must not include secrets, raw provider payloads, private service
endpoints, uploaded file bodies, raw prompts, local database details, runtime
logs, local upload paths, or broad native response blobs.

## Fail Closed Rules

The contract must fail closed in these cases:

| Case | Expected behavior |
| --- | --- |
| Real citation has no `evidence_id` | Reject before persistence or mark citation support blocked. |
| `document_chunk` lacks `chunk_id` | Reject citation binding; do not fall back to a whole-document PASS. |
| `document_chunk` lacks both PA document id and `external_doc_id` | Reject citation binding; PA cannot link history to native knowledge. |
| `wiki_page` lacks `wiki_page_id` or stable slug-derived id | Reject citation binding or mark Wiki citation support blocked. |
| Citation does not match retrieved evidence | Checker fails validation. |
| Locator cannot resolve a stored target | Return unavailable with a reason; do not fabricate a Library or Wiki route. |
| Native AgentQA/custom Agent lacks citation ids | Mark P1 result partial/blocked; do not count it as citation PASS. |
| Metadata contains unsafe or unallowlisted fields | Redact or drop the field before debug/report/browser output. |

## History, Browser, And Report Expectations

History and output records must preserve citation state:

- `GeneratedOutputRead` exposes total, WeKnora, mock, document, Wiki, warning,
  and evidence-state counts.
- `CitationRead` hydrates `evidence_id`, `source_type`, and `wiki_page_id`
  from stored metadata when the SQL citation row does not have dedicated
  columns for every field.
- History filters must distinguish `weknora`, `mock_only`, `mixed`,
  `no_evidence`, and source-type filters.
- Browser citation rendering must show document and Wiki citations truthfully;
  if a locator response is unavailable, the UI should show unavailable/blocked
  state instead of a broken jump.
- Reports must include `source`, `source_type`, `evidence_id`, native ids,
  locator expectations, and evidence category labels when claiming PASS.

No frontend files changed in this task, so browser validation is not required
for this PASS. Future frontend changes to RAG debug, Wiki, knowledge QA, or
History citation rendering must run browser checks for the affected page.

## Focused Validation

Focused smoke:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_citation_contract_m1.py
```

Expected coverage:

- WeKnora search-shaped document evidence maps to `source=weknora_api`,
  `source_type=document_chunk`, `evidence_id`, `chunk_id`, and
  `external_doc_id`.
- Wiki evidence maps to `source=weknora_api`, `source_type=wiki_page`,
  `evidence_id`, and `wiki_page_id`.
- Non-mock evidence missing required native ids fails closed.
- Saved citations persist through PA output/history models.
- Locator fields route persisted document citations to Library and Wiki
  citations to Wiki in a temporary local test database.

Safety/report checks:

```bash
test -f docs/WEKNORA_FIRST_CITATION_CONTRACT.md
rg -n "source_type|evidence_id|chunk_id|external_doc_id|wiki_page_id|locator|fail closed|allowlist" docs/WEKNORA_FIRST_CITATION_CONTRACT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_CITATION_CONTRACT.md
git diff --check
```

## Conclusion

`WF-P0-05` preserves the PA citation/evidence contract for the current
WeKnora-first P0 native document and RAG paths. The contract is strict: real
non-mock citations must carry `source`, `source_type`, `evidence_id`, native ids
where applicable, safe locator fields, and allowlisted metadata. Missing native
ids fail closed or become blocked/backlog; they are not silently converted into
PASS evidence.
