# PHASE3 WeKnora API Map

> Task: P3-M1-B1
>
> Scope: audit WeKnora RAG API and response mapping for PA `KnowledgeBackend Adapter`.
>
> Guardrail: no PA product runtime code or upstream WeKnora source code is changed by this task.

## Audited Sources

- WeKnora OpenAPI docs: `../docs/swagger.yaml`, `../docs/swagger.json`
- WeKnora Go client: `../client/client.go`, `../client/knowledge.go`, `../client/chunk.go`, `../client/knowledgebase.go`, `../client/session.go`, `../client/message.go`
- WeKnora routes: `../internal/router/router.go`
- WeKnora handlers: `../internal/handler/knowledge.go`, `../internal/handler/chunk.go`, `../internal/handler/knowledgebase.go`, `../internal/handler/session/qa.go`
- WeKnora services/types: `../internal/application/service/knowledge_create.go`, `../internal/application/service/knowledgebase_search.go`, `../internal/application/service/session_knowledge_qa.go`, `../internal/types/knowledge.go`, `../internal/types/search.go`, `../internal/types/chat.go`, `../internal/types/message.go`, `../internal/errors/errors.go`, `../internal/middleware/error_handler.go`
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

## Acceptance Checklist For B1

- upload API identified and mapped to PA `KnowledgeDocument`.
- status API identified and mapped to PA `DocumentStatus`.
- retrieve API identified and mapped to PA `Evidence`.
- chunk preview API identified and mapped to PA evidence/citation metadata.
- citation source mapping documented without requiring a nonexistent dedicated citation endpoint.
- error mapping documented for PA adapter implementation.
- unknowns/gaps recorded for B2/B3/B4.
