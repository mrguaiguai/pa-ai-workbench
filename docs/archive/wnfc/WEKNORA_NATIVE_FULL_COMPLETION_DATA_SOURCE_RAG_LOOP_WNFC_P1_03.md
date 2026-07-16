# WNFC-P1-03 Data Source RAG Loop Evidence

Date: 2026-06-24

Task: `WNFC-P1-03: Data-source to KB/RAG evidence loop`

Decision: PASS

Evidence type: `live_api+native_citation_current_run`

## Scope

This task proves that a synced external data source can become WeKnora native
knowledge and then be retrieved and answered through PA with traceable native
evidence/citations.

This task uses the already available no-credential RSS connector path for
evidence. It does not complete `WNFC-P1-01`, because credential-bearing
Notion/Yuque/Feishu setup still needs a real credential and accessible
workspace.

The WNFC aggregate score remains `11.50 / 14 = 82.1%` because the overall
Data sources/connectors group is not `full-complete` while the credential
connector blocker remains open.

## Native Source Audit

No WeKnora Go source change was required.

Audited native data-source routes and services:

- `internal/router/router.go`
- `internal/handler/datasource.go`
- `internal/application/service/datasource_service.go`
- `internal/datasource/connector/rss/connector.go`
- `internal/application/service/knowledge_create.go`
- `internal/handler/knowledge.go`

Real native path:

1. `POST /api/v1/datasource/:id/sync` calls `DataSourceService.ManualSync`.
2. `DataSourceService.ProcessSync` fetches connector items and calls
   `ingestItem`.
3. RSS `FetchedItem` contains Markdown bytes from the live feed.
4. `ingestItem` writes content through `KnowledgeService.CreateKnowledgeFromFile`.
5. WeKnora parses, chunks, embeds, and indexes the resulting native knowledge.
6. PA calls `/api/rag/debug` and `/api/rag/knowledge-chat`, which route to
   native `/api/v1/knowledge-search` and `/api/v1/knowledge-chat/{session_id}`.

PA-first was sufficient because WeKnora already exposes the sync, knowledge,
search, and knowledge-chat execution path needed for this evidence loop.

## PA Changes

Added `backend/scripts/check_weknora_native_data_source_rag_loop.py`.

The smoke:

- creates a temporary real RSS data source through the native API;
- triggers sync through the PA confirmation-gated BFF;
- records `weknora_data_source_sync` through `NativeMutationAudit`;
- waits for a new `source=rss` native knowledge item to reach indexed status;
- runs PA RAG debug scoped by that native knowledge id;
- runs PA native knowledge-chat scoped by that native knowledge id;
- verifies saved PA citations carry `source=weknora_api`,
  `source_type=document_chunk`, `external_doc_id`, and `evidence_id`;
- removes the temporary data source after validation.

Updated `backend/scripts/check_weknora_native_full_completion_acceptance.py` so
the WNFC acceptance checker includes this P1-03 report.

## Current-Run Evidence

Python compile:

```text
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_data_source_rag_loop.py backend/scripts/check_weknora_native_full_completion_acceptance.py
PASS
```

Live API and native citation smoke:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_data_source_rag_loop.py

WeKnora native data source to KB/RAG evidence loop
- decision: PASS
- evidence_type: live_api+native_citation_current_run
- native_sync: rss_source=created sync=audit_succeeded
- kb_index: rss_knowledge=indexed
- rag_debug: total=1 scoped_native_evidence=passed
- knowledge_chat: references=2 saved_citations=2 guard=passed
- history: native_knowledge_chat output listed
- cleanup: temporary data source removed; synced KB evidence was validated before cleanup
```

Acceptance harness:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_full_completion_acceptance.py

WNFC native full completion acceptance check passed
- evidence_type: checker_execution
- mode: in-progress
- reports checked: 6
- task rows: 23
- completed tasks: 6
- unfinished tasks: 17
- current score: 11.50/14 = 82.1%
- target score: 14.00/14 = 100.0%
- web_search: excluded
- final_ready: false
- browser_hooks: WNFC-P6-01 desktop/mobile matrix and WNFC-P6-02 final report hooks present
```

Diff and sensitive checks:

```text
git diff --check
PASS

rg sensitive-value scan over this report and the WNFC spec
PASS
```

Evidence boundary:

- The script does not print feed URLs, raw external resource names, raw answers,
  raw chunks, raw connector config, provider payloads, logs, local database
  paths, or credentials.
- RSS is a real native no-credential connector path, not a mock connector.
- The RAG/chat proof is scoped by the newly synced native knowledge id, so it
  is not a broad keyword hit against stale KB content.
- Browser evidence was not required because this task did not touch UI files.

## Remaining Blocker

`WNFC-P1-01` remains blocked:

- Provider/module: credential-bearing native data source connector
  (Notion/Yuque/Feishu).
- Missing item: one real credential plus an accessible workspace/resource with
  permission to list and sync content.
- Expected config location: native WeKnora data-source credential/config API
  surfaced through PA masked status.
- Minimal access: read/list/sync permission for one small workspace/resource.
- Post-supply validation: credential setup, resources, validation, sync logs,
  sync, pause/resume/delete audit, and RAG/chat citation evidence through PA.
