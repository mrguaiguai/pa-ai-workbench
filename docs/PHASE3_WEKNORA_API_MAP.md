# PHASE3 WeKnora API Map

> Task: P3-M1-B1, P3-M1-C1
>
> Scope: audit WeKnora RAG/Wiki API and response mapping for PA `KnowledgeBackend Adapter`.
>
> Guardrail: no PA product runtime code or upstream WeKnora source code is changed by this task.

## Audited Sources

- WeKnora OpenAPI docs: `../docs/swagger.yaml`, `../docs/swagger.json`
- WeKnora Go client: `../client/client.go`, `../client/knowledge.go`, `../client/chunk.go`, `../client/knowledgebase.go`, `../client/session.go`, `../client/message.go`
- WeKnora routes: `../internal/router/router.go`
- WeKnora handlers: `../internal/handler/knowledge.go`, `../internal/handler/chunk.go`, `../internal/handler/knowledgebase.go`, `../internal/handler/session/qa.go`
- WeKnora services/types: `../internal/application/service/knowledge_create.go`, `../internal/application/service/knowledgebase_search.go`, `../internal/application/service/session_knowledge_qa.go`, `../internal/types/knowledge.go`, `../internal/types/search.go`, `../internal/types/chat.go`, `../internal/types/message.go`, `../internal/errors/errors.go`, `../internal/middleware/error_handler.go`
- WeKnora Wiki routes/handlers/services: `../internal/router/router.go`, `../internal/handler/wiki_page.go`, `../internal/application/service/wiki_page.go`, `../internal/application/service/wiki_ingest.go`, `../internal/application/service/wiki_ingest_batch.go`, `../internal/application/service/wiki_ingest_cite.go`, `../internal/types/wiki_page.go`, `../internal/types/interfaces/wiki_page.go`
- PA target schemas: `knowledge_engine/base.py`, `knowledge_engine/schemas.py`, `knowledge_engine/backends/weknora_api_backend.py`

## Authentication And Envelope

WeKnora client authentication supports:

| Credential | Header | PA M1 mapping |
| --- | --- | --- |
| API key | `X-API-Key: <token>` | Preferred for `WEKNORA_SERVICE_TOKEN` if the M1 service account issues API keys. |
| Bearer token | `Authorization: Bearer <token>` | Acceptable if M1 uses a JWT-style service token. |
| Tenant override | `X-Tenant-ID: <tenant_id>` | Do not send by default. Only use if the service account is explicitly allowed for cross-tenant access. |

Normal JSON success envelope:

```json
{
  "success": true,
  "data": {}
}
```

List responses may also include:

```json
{
  "total": 0,
  "page": 1,
  "page_size": 10
}
```

App error envelope:

```json
{
  "success": false,
  "error": {
    "code": 1000,
    "message": "error message",
    "details": {}
  }
}
```

## API Surface For PA M1 RAG

Use the runtime base URL plus `/api/v1` for the API routes below. `GET /health` is outside `/api/v1`.

| PA need | WeKnora endpoint | Method | Request | Response data | PA adapter method | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| health | `/health` | GET | none | `{ "status": "ok" }` | `health()` | Already used by the P3-M1-A4 smoke script. |
| upload file | `/api/v1/knowledge-bases/{kb_id}/knowledge/file` | POST multipart | `file`, optional `fileName`, `metadata`, `enable_multimodel`, `tag_id`, `channel` | `Knowledge` | `upload_document()` | Main PA document upload route for PDF/DOCX/Markdown and other supported files. |
| upload URL | `/api/v1/knowledge-bases/{kb_id}/knowledge/url` | POST JSON | `url`, optional `file_name`, `file_type`, `enable_multimodel`, `title`, `tag_id`, `channel` | `Knowledge` | later optional | URL ingestion is not required for the first PA file-upload acceptance path. |
| create manual knowledge | `/api/v1/knowledge-bases/{kb_id}/knowledge/manual` | POST JSON | `title`, `content`, `status`, optional `tag_id`, `channel` | `Knowledge` | later optional / Wiki bridge candidate | Useful only if PA must create WeKnora-searchable Markdown without file upload. |
| list KB knowledge | `/api/v1/knowledge-bases/{kb_id}/knowledge` | GET | `page`, `page_size`, optional filters | list of `Knowledge` | optional sync/list | Useful for reconciliation, not required for `retrieve()`. |
| status | `/api/v1/knowledge/{knowledge_id}` | GET | path id | `Knowledge` | `get_document_status()` | Use `parse_status`, `pending_subtasks_count`, `error_message`, `processed_at`. |
| stages/spans | `/api/v1/knowledge/{knowledge_id}/spans` or `/stages` | GET | optional `attempt` | parse stage tree | optional diagnostics | M2-quality timeline details; B2 can skip unless status UX needs it. |
| chunk preview | `/api/v1/chunks/{knowledge_id}` | GET | `page`, `page_size`, repeated `chunk_type` | list of `Chunk` plus pagination | `list_document_chunks()` candidate | Defaults to text chunks. Handler caps `page_size` to 100. |
| chunk by id | `/api/v1/chunks/by-id/{chunk_id}` | GET | path id | `Chunk` | citation drilldown candidate | Useful for validating saved citation external IDs. |
| retrieve | `/api/v1/knowledge-search` | POST JSON | `query`, `knowledge_base_id`, `knowledge_base_ids`, `knowledge_ids` | list of `SearchResult` | `retrieve()` | Current router/client route. Swagger still documents `/sessions/search`; see gaps. |
| retrieve with low-level knobs | `/api/v1/knowledge-bases/{kb_id}/hybrid-search` | GET with JSON body | `SearchParams` | list of `SearchResult` | optional `retrieve()` variant | Supports thresholds, `match_count`, disabled keyword/vector flags, tag and knowledge scopes. GET-with-body may be awkward for some clients. |
| answer with WeKnora LLM | `/api/v1/knowledge-chat/{session_id}` | POST SSE | chat request | stream `answer` and `references` | not PA M1 main path | PA Agent must keep its own workflow. Use only as source reference for citation shape. |

## Upload And Status Mapping

### Raw `Knowledge`

Relevant WeKnora fields:

```text
id
knowledge_base_id
tag_id
type
title
description
source
channel
parse_status
pending_subtasks_count
summary_status
enable_status
embedding_model_id
file_name
file_type
file_size
file_hash
metadata
created_at
updated_at
processed_at
error_message
```

### PA `KnowledgeDocument`

| WeKnora field | PA field | Mapping rule |
| --- | --- | --- |
| `id` | `external_doc_id` | Store as the WeKnora document/knowledge id. |
| PA local document id or metadata | `document_id` | Keep PA id if the upload was initiated by PA; otherwise null. |
| `title`, fallback `file_name` | `title` | Prefer `title`; use file name when title is empty. |
| `parse_status` | `status` | Map through the PA status table below. |
| constant | `source` | Always `weknora_api`. |
| `knowledge_base_id`, `tag_id`, `type`, `channel`, `file_type`, `file_size`, `summary_status`, `enable_status`, `processed_at`, `error_message`, `metadata` | `metadata` | Keep small display/control fields only. Do not store full file path or long raw content in PA metadata. |

### PA `DocumentStatus`

| WeKnora `parse_status` | PA status | Notes |
| --- | --- | --- |
| `pending` | `uploaded` | Created but not yet processed. |
| `processing` | `parsing` | WeKnora combines DocReader, chunking, and embedding under this broad state. If span API is used, PA may refine the visible step. |
| `finalizing` | `embedding` or `indexed` with enrichment pending | The document is queryable for vector search but enrichment subtasks remain. For M1, prefer showing `embedding` or `indexed` plus `pending_subtasks_count` metadata rather than hiding the nuance. |
| `completed` | `indexed` | Terminal success. |
| `failed` | `failed` | Copy `error_message` into PA `error_message`. |
| `deleting` | `unknown` | Not part of PA M1 happy path. Keep raw status in metadata. |
| `cancelled` | `failed` | Treat as non-indexed for PA UX unless a later reparse succeeds. |
| missing/other | `unknown` | Record raw value in metadata. |

## Retrieve And Evidence Mapping

### Raw `SearchResult`

Relevant WeKnora fields:

```text
id
content
knowledge_id
chunk_index
knowledge_title
start_at
end_at
seq
score
match_type
sub_chunk_id
metadata
chunk_type
parent_chunk_id
image_info
knowledge_filename
knowledge_source
knowledge_channel
chunk_metadata
matched_content
knowledge_description
knowledge_base_id
```

`client/knowledgebase.go` notes that `score` is an RRF-style fused score, not raw vector similarity. `match_type` identifies vector, keyword, FAQ, wiki, graph, web, direct-load, or data-analysis style matches.

### PA `Evidence`

| WeKnora field | PA field | Mapping rule |
| --- | --- | --- |
| `id` | `chunk_id` | Treat as WeKnora chunk id for document evidence. |
| `knowledge_id` | `external_doc_id` | Parent WeKnora knowledge/document id. |
| PA local doc mapping, if known | `document_id` | Resolve through PA upload mapping table/cache when available. |
| `knowledge_title`, fallback `knowledge_filename` | `title` | Required for citation display. |
| `content`, fallback `matched_content` | `text` | Use sanitized excerpt returned by WeKnora. Do not log full content. |
| `score` | `score` | Preserve numeric score; store score semantics in metadata. |
| constant | `source` | Always `weknora_api`. |
| constant unless wiki match is confirmed | `source_type` | `document_chunk` for normal RAG results. If `match_type` or metadata proves a wiki hit, map to `wiki_page`. |
| derived | `evidence_id` | `document_chunk:{id}` for document chunks; `wiki_page:{wiki_id}` for wiki evidence. |
| `knowledge_base_id`, `chunk_index`, `start_at`, `end_at`, `seq`, `match_type`, `chunk_type`, `parent_chunk_id`, `sub_chunk_id`, `knowledge_source`, `knowledge_channel`, `chunk_metadata`, `metadata` | `metadata` | Keep enough for citation trace and preview. |

Minimum non-mock `Evidence` required for PA M1:

```text
evidence_id
source_type=document_chunk
source=weknora_api
chunk_id
external_doc_id
title
text
score
metadata.knowledge_base_id
metadata.chunk_index
metadata.match_type
```

## Chunk Preview Mapping

### Raw `Chunk`

Relevant WeKnora fields:

```text
id
seq_id
knowledge_id
knowledge_base_id
tag_id
content
chunk_index
is_enabled
status
start_at
end_at
pre_chunk_id
next_chunk_id
chunk_type
parent_chunk_id
relation_chunks
indirect_relation_chunks
metadata
content_hash
image_info
created_at
updated_at
```

### PA preview shape

| WeKnora field | PA display/mapping |
| --- | --- |
| `id` | external chunk id / `chunk_id` |
| `knowledge_id` | `external_doc_id` |
| `content` | preview text / evidence text |
| `chunk_index`, `seq_id` | ordering |
| `start_at`, `end_at` | citation location metadata |
| `chunk_type`, `parent_chunk_id`, `pre_chunk_id`, `next_chunk_id` | context navigation metadata |
| `status`, `is_enabled` | filter disabled/non-indexed chunks out of M1 evidence when needed |
| `metadata`, `image_info` | preserve as small metadata only |

## Citation Mapping Decision

WeKnora does not expose a dedicated RAG `citation` HTTP resource in the audited files. The citation-ready source material is:

| Source | Raw fields | PA use |
| --- | --- | --- |
| `SearchResult` from `/api/v1/knowledge-search` or hybrid search | `id`, `knowledge_id`, `knowledge_title`, `content`, `score`, `chunk_index`, `start_at`, `end_at`, `match_type` | Primary source for PA `Evidence` and `CitationBuilder`. |
| `Message.knowledge_references` / SSE `references` | array of `SearchResult` | Reference shape only. PA Agent should not call WeKnora LLM chat as the main M1 workflow. |
| Wiki `source_refs` and `chunk_refs` | source knowledge ids and cited chunk ids | Wiki citation mapping belongs to P3-M1-C tasks, but B1 retrieve mapping must preserve chunk ids so Wiki citations can later be validated. |
| `/api/v1/chunks/by-id/{chunk_id}` | full `Chunk` | Citation drilldown / validation endpoint. |

PA citation rules for B3/B4:

1. Build citations from normalized PA `Evidence`, not from raw WeKnora JSON.
2. For document evidence, require `evidence_id`, `chunk_id`, `external_doc_id`, `title`, and non-empty `text`.
3. Set `external_source_id` to WeKnora chunk id.
4. Keep `knowledge_base_id`, `chunk_index`, `start_at`, `end_at`, and `match_type` in citation metadata.
5. If a result is later confirmed as wiki evidence, require `wiki_page_id` or external wiki id and set `source_type=wiki_page`.

## Error Mapping

| HTTP / WeKnora error | WeKnora envelope/code | PA adapter error | Retryable | Notes |
| --- | --- | --- | --- | --- |
| network error / DNS / connection refused | none | `WeKnoraUnavailableError` | yes | Current PA code only has `KnowledgeBackendUnavailableError`; B2/B3 should add typed WeKnora errors or map internally. |
| timeout | none or HTTP timeout | `WeKnoraTimeoutError` | yes | Use `WEKNORA_TIMEOUT_SECONDS`. |
| 400 | code `1000` or validation details | `WeKnoraResponseMappingError` or `WeKnoraDocumentError` | no | Bad request, invalid metadata, missing query, or unsupported shape. |
| 401 | code `1001` | `WeKnoraAuthError` | no | Token missing/expired/invalid. |
| 403 | code `1002` | `WeKnoraAuthError` | no | Permission or tenant/KB access failure. |
| 404 | code `1003` | `WeKnoraDocumentError` | no | Missing document, chunk, or KB. |
| 409 | code `1005` | `WeKnoraDocumentError` | no | Duplicate file/URL returns existing knowledge in some upload paths; adapter can treat as success only if PA policy accepts reuse. |
| 429 | code `1006` | `WeKnoraRateLimitError` | yes | Back off. |
| 500 | code `1007` | `WeKnoraUnavailableError` or operation-specific error | maybe | Do not pass raw stack/trace to PA frontend. |
| 503 | code `1008` | `WeKnoraUnavailableError` | yes | Vector store, model, DB, Redis, or DocReader may be unavailable. |
| unknown JSON shape | success envelope missing `data`, non-object/list where expected | `WeKnoraResponseMappingError` | no | Record operation and request id only. |

PA API error shape should remain:

```text
status_code
error_code
message
operation
retryable
request_id
```

Do not expose WeKnora token, raw upstream stack traces, full prompts, full documents, or long chunks.

## B2/B3 Implementation Notes

Recommended M1 defaults:

| Adapter method | Endpoint | Required config |
| --- | --- | --- |
| `upload_document()` | `POST /api/v1/knowledge-bases/{WEKNORA_DEFAULT_KB_ID}/knowledge/file` | `WEKNORA_BASE_URL`, `WEKNORA_SERVICE_TOKEN`, `WEKNORA_DEFAULT_KB_ID` |
| `get_document_status()` | `GET /api/v1/knowledge/{external_doc_id}` | `WEKNORA_BASE_URL`, `WEKNORA_SERVICE_TOKEN` |
| `list_document_chunks()` | `GET /api/v1/chunks/{external_doc_id}` | same |
| `retrieve()` | `POST /api/v1/knowledge-search` | `WEKNORA_DEFAULT_KB_ID` unless request filters provide `knowledge_base_ids` |

Suggested `retrieve()` request mapping:

| PA input | WeKnora request |
| --- | --- |
| `query` | `query` |
| `top_k` | No direct field in `/knowledge-search`; service uses tenant retrieval config. For direct top-k control, use `hybrid-search.match_count` after live confirmation. |
| `filters.document_ids` | `knowledge_ids` |
| `filters.knowledge_base_ids` or default KB | `knowledge_base_ids` |
| `filters.business_area`, `filters.document_type` | No direct raw field in `/knowledge-search`; possible future mapping through tags/metadata if WeKnora KB taxonomy is configured. |
| `filters.tag_ids` | Not supported by `/knowledge-search` request; supported by low-level `SearchParams` as `tag_ids`. |
| `filters.source_type` | No direct filter for document/wiki in the audited `/knowledge-search` request. Filter after normalization unless a later Wiki-specific API is used. |

## Unknowns And Gaps

| Gap | Evidence | Impact | Follow-up |
| --- | --- | --- | --- |
| Swagger route mismatch for direct retrieval | Swagger documents `/sessions/search`; router and Go client use `/api/v1/knowledge-search`. | Smoke scripts must verify the live service route before B3. | In P3-M1-B3, try `/api/v1/knowledge-search` first and report exact failure if route differs in deployed build. |
| `top_k` control is indirect on `/knowledge-search` | `SearchKnowledgeRequest` has only `query`, `knowledge_base_id(s)`, `knowledge_ids`; service uses tenant retrieval config. | PA `retrieve(top_k=...)` may not be exact if using `/knowledge-search`. | For exact `top_k`, evaluate `hybrid-search` with `match_count`, or accept backend-configured top-k for M1. |
| `hybrid-search` is documented as GET with body | Handler binds JSON body on a GET route. | Some HTTP clients/proxies may drop GET bodies. | Prefer `/knowledge-search` for M1 unless exact knobs are required. |
| Upload returns broad `processing` status | WeKnora `parse_status` does not split parse/chunk/embed in the main `Knowledge` response. | PA status UI may be less granular without span API. | Use `/knowledge/{id}/spans` in M2 or if B2 needs detailed timeline. |
| No dedicated RAG citation API | Citation material appears as `SearchResult`, message `knowledge_references`, and Wiki refs. | PA must own CitationBuilder mapping. | P3-M1-B4 should add contract tests for `SearchResult -> Evidence -> Citation`. |
| Wiki evidence discrimination is not fully resolved in RAG search results | `SearchResult.match_type` has wiki-like categories, but B1 did not run live data. | Adapter may default to `document_chunk` until Wiki tasks confirm shape. | P3-M1-C1/C2 should audit Wiki APIs and live wiki retrieval response. |
| Service account token type is deployment-dependent | Client supports both `X-API-Key` and Bearer. Current PA backend sends Bearer only. | M1 auth may fail if the issued credential is API-key-only. | B2 should support `X-API-Key` for `WEKNORA_SERVICE_TOKEN`, or add `WEKNORA_AUTH_HEADER` selection. |

## C1 Wiki API Surface For PA M1

WeKnora Wiki routes are registered under `/api/v1/knowledgebase/{kb_id}/wiki`.
Every handler first validates that the knowledge base exists and has Wiki
enabled, so PA must pass a Wiki-capable `WEKNORA_DEFAULT_KB_ID` or an explicit
Wiki KB id.

| PA need | WeKnora endpoint | Method | Request | Response data | PA adapter method | M1 decision |
| --- | --- | --- | --- | --- | --- | --- |
| search Wiki pages | `/api/v1/knowledgebase/{kb_id}/wiki/search` | GET | `q`, optional `limit` | `{ "pages": [WikiPage] }` | `search_wiki()` | Direct call for C2. Map to `WikiPageSummary`. |
| list Wiki pages | `/api/v1/knowledgebase/{kb_id}/wiki/pages` | GET | `page_type`, `status`, `query`, `page`, `page_size`, `sort_by`, `sort_order` | `WikiPageListResponse` | optional C2 list/search support | Use when PA needs page directory or status-filtered reads. |
| read by slug | `/api/v1/knowledgebase/{kb_id}/wiki/pages/{slug}` | GET | path slug, wildcard supports nested slugs | `WikiPage` | `read_wiki_page()` | Direct call for C2. Preserve slug addressing in PA. |
| create page or draft | `/api/v1/knowledgebase/{kb_id}/wiki/pages` | POST | `WikiPage` JSON | `WikiPage` | `create_wiki_page()` / draft sync candidate | Direct WeKnora write is possible. PA still needs local draft bridge for output-derived drafts before sync. |
| update page | `/api/v1/knowledgebase/{kb_id}/wiki/pages/{slug}` | PUT | `WikiPage` JSON | `WikiPage` | `update_wiki_page()` | Direct call for C3. WeKnora bumps version only for user-visible content/status changes. |
| archive/delete page | `/api/v1/knowledgebase/{kb_id}/wiki/pages/{slug}` | DELETE | path slug | 204 | later optional | Not required for M1 PA output-to-draft happy path. |
| structured index | `/api/v1/knowledgebase/{kb_id}/wiki/index` | GET | optional `types`, `limit`, `cursor` | `WikiIndexResponse` | `index_wiki_page()` status/display candidate | This is a read-side index/directory view, not a publish/index job trigger. |
| operation log | `/api/v1/knowledgebase/{kb_id}/wiki/log` | GET | `cursor`, `limit` | `WikiLogEntryListResponse` | status display candidate | Useful for C4 status, but PA should not depend on log text for correctness. |
| stats | `/api/v1/knowledgebase/{kb_id}/wiki/stats` | GET | none | `WikiStats` | backend status display candidate | Contains `pending_tasks`, `pending_issues`, `is_active`. |
| graph | `/api/v1/knowledgebase/{kb_id}/wiki/graph` | GET | `mode`, `center`, `depth`, `types`, `limit` | `WikiGraphData` | out of M1 adapter path | Product graph UI is not required for PA M1. |
| lint/issues | `/api/v1/knowledgebase/{kb_id}/wiki/lint`, `/issues` | GET/PUT | issue filters/status | lint/issues shapes | later quality workflow | Useful in M2/M3, not required for C2/C3. |
| rebuild links / auto-fix | `/api/v1/knowledgebase/{kb_id}/wiki/rebuild-links`, `/auto-fix` | POST | none | message / report | admin maintenance only | Do not call from PA Agent workflows in M1. |

## C1 Raw WikiPage Shape

Relevant WeKnora `WikiPage` fields:

```text
id
tenant_id
knowledge_base_id
slug
title
page_type
status
content
summary
aliases
source_refs
chunk_refs
in_links
out_links
page_metadata
version
created_at
updated_at
deleted_at
```

Page types audited in `internal/types/wiki_page.go`:

```text
summary
entity
concept
index
log
synthesis
comparison
```

Statuses audited in `internal/types/wiki_page.go`:

```text
draft
published
archived
```

## C1 PA WikiPage Mapping

Adapter output must normalize WeKnora fields into PA schemas instead of exposing
the raw WeKnora response.

### PA `WikiPageSummary`

| WeKnora field | PA field | Mapping rule |
| --- | --- | --- |
| `slug` | `slug` | Required stable address. Preserve nested slugs exactly after URL-decoding. |
| `title` | `title` | Required display title. |
| `page_type` | `page_type` | Preserve WeKnora type. Unknown values stay in metadata and map through as strings. |
| `summary` | `summary` | Use empty string only if WeKnora omits it. Do not derive from full content in adapter. |
| constant | `source` | Always `weknora_api`. |
| `id`, `knowledge_base_id`, `status`, `aliases`, `source_refs`, `chunk_refs`, `version`, `updated_at`, `page_metadata` | `metadata` | Keep small provenance and display fields. Do not duplicate full `content`. |

### PA `WikiPage`

| WeKnora field | PA field | Mapping rule |
| --- | --- | --- |
| `slug` | `slug` | Required. |
| `title` | `title` | Required. |
| `page_type` | `page_type` | Preserve. |
| `summary` | `summary` | Preserve. |
| `content` | `content` | Markdown body. Do not log full body in adapter errors. |
| `source_refs`, `chunk_refs` | `citations` | Convert refs into PA `Evidence` only when there is enough information to build traceable evidence. Otherwise preserve refs in metadata and leave citations empty. |
| constant | `source` | Always `weknora_api`. |
| `id`, `knowledge_base_id`, `status`, `aliases`, `source_refs`, `chunk_refs`, `in_links`, `out_links`, `page_metadata`, `version`, timestamps | `metadata` | Keep external IDs and source refs for citation drilldown and future status UI. |

Minimum `WikiPage` metadata for PA M1:

```text
id
knowledge_base_id
status
source_refs
chunk_refs
version
source=weknora_api
```

## C1 Draft / Publish / Index Decisions

| Capability | WeKnora support | PA M1 decision | Follow-up task |
| --- | --- | --- | --- |
| output to draft | No dedicated `output -> draft` endpoint. `POST /wiki/pages` accepts `status=draft`, but PA output ids do not exist in WeKnora. | Keep PA local draft creation from `GeneratedOutput`; sync to WeKnora on create/update only after PA has normalized slug/title/content/source refs. Store WeKnora `id`, `slug`, `knowledge_base_id`, and `status` in PA metadata. | C3 |
| manual create draft/page | `POST /wiki/pages` with `WikiPage.status`; service defaults empty status to `published`. | When PA wants a draft, explicitly send `status=draft`. Never rely on WeKnora default. | C3 |
| publish | No separate publish route. Publishing is a status transition through `PUT /wiki/pages/{slug}` with `status=published`. | PA publish action should call update with `status=published`, then refresh read/status. | C4 |
| index visibility | Wiki pages are synchronized into WeKnora retrieval through WeKnora Wiki internals; `GET /wiki/index` is a directory view, not a reindex endpoint. | PA should treat WeKnora `status=published` plus successful read/search as M1 visible/indexed evidence. Use `/wiki/stats` and `/wiki/log` only for status hints. | C4 |
| source refs | `source_refs` store document-level refs in `"<knowledge_id>|<doc_title>"`; `chunk_refs` store concrete chunk ids for cited chunks. | PA citations can be built only when `chunk_refs` or source metadata can be resolved to PA `Evidence`. Document-level `source_refs` alone are provenance, not citation evidence. | C5 |
| Wiki search/read | Dedicated search/read routes exist. | C2 should call WeKnora directly through adapter and map to PA `WikiPageSummary` / `WikiPage`. | C2 |

## C1 Source Reference And Citation Mapping

WeKnora Wiki source refs are provenance-rich but not always citation-complete.
The ingest pipeline records:

| WeKnora field | Meaning | PA use |
| --- | --- | --- |
| `source_refs` | Document-level refs using `knowledge_id|doc_title`. | Store in `WikiPage.metadata.source_refs`; optionally map to PA source document ids if PA has upload mappings. |
| `chunk_refs` | Concrete WeKnora chunk ids cited by a generated page. Empty for summary pages by design. | Candidate source for `Evidence.source_type=wiki_page` or document-chunk citations after chunk lookup. |
| `page_metadata` | Arbitrary page metadata. | Preserve small fields; never assume PA output ids exist here unless PA wrote them. |
| `in_links` / `out_links` | Wiki graph links by slug. | Display/navigation metadata, not citation evidence. |

C5 must fail closed:

1. If a Wiki citation has `chunk_refs`, resolve chunk ids through `/api/v1/chunks/by-id/{chunk_id}` or retrieve metadata before creating PA citations.
2. If only `source_refs` exist, show provenance but do not create a non-mock PA citation unless the parent document id and excerpt can be resolved.
3. If a RAG result is confirmed as Wiki evidence, set `source_type=wiki_page`, `wiki_page_id=<WeKnora page id or slug>`, `source=weknora_api`, and preserve `slug`, `knowledge_base_id`, and `chunk_refs` in metadata.

## C1 Unknowns And Gaps

| Gap | Evidence | Impact | Follow-up |
| --- | --- | --- | --- |
| No dedicated publish endpoint | Wiki handler exposes create/update/delete, not `/publish`. | PA must model publish as `status=published` update. | C4 smoke should verify status transition. |
| `GET /wiki/index` is a directory view | Handler calls `GetIndexView`; it does not trigger retrieval indexing. | PA cannot use it as a reindex command. | C4 should define indexed/visible acceptance via search/read. |
| No direct PA output identity in WeKnora | WeKnora `WikiPage` has `page_metadata`, but no PA output schema. | PA must write output linkage into metadata when syncing drafts. | C3. |
| `source_refs` are document-level strings | Types document the `knowledge_id|doc_title` convention. | Not enough for exact citation excerpt by itself. | C5 must resolve chunk refs or retrieve evidence. |
| Summary pages intentionally lack chunk refs | WeKnora type comments say summary pages are document-level synopses and do not carry chunk-level citations. | PA should present provenance without pretending exact citation spans. | C5. |
| Wiki-enabled KB requirement | Handler rejects KBs where Wiki is not enabled. | Misconfigured `WEKNORA_DEFAULT_KB_ID` will make all Wiki calls fail. | A2/C2 smoke should verify Wiki-enabled KB id. |
| Swagger path omits runtime `/api/v1` prefix | Router mounts Wiki routes under the v1 group; swagger path starts at `/knowledgebase/...`. | Adapter should call `/api/v1/knowledgebase/{kb_id}/wiki/...` consistently with existing backend base URL convention. | C2. |

## Acceptance Checklist For B1

- upload API identified and mapped to PA `KnowledgeDocument`.
- status API identified and mapped to PA `DocumentStatus`.
- retrieve API identified and mapped to PA `Evidence`.
- chunk preview API identified and mapped to PA evidence/citation metadata.
- citation source mapping documented without requiring a nonexistent dedicated citation endpoint.
- error mapping documented for PA adapter implementation.
- unknowns/gaps recorded for B2/B3/B4.

## Acceptance Checklist For C1

- Wiki search/read/create/update/index/log/stats API routes identified.
- `WikiPage` and `WikiPageSummary` field mapping documented.
- draft, publish, index, and source ref decisions documented.
- direct WeKnora calls vs PA local compensation are explicit.
- citation/source refs risks recorded for C5.
