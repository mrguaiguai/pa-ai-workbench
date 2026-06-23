# WeKnora Native Vector Store Management Live Report

> Task: `WNX-P2-04`
>
> Date: 2026-06-23
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live API/browser evidence.

## Scope

`WNX-P2-04` upgrades PA vector-store visibility from read-only status to a
safe live-partial management surface. PA now reads WeKnora native vector-store
types, configured-store list, active KB binding, embedding readiness, and a
sanitized per-store detail path.

External vector-store probes are confirmation-gated because native tests may
touch external infrastructure and can persist detected version metadata for
database-backed stores. PA does not expose raw vector store IDs, connection
config, index config, endpoints, hosts, ports, DSNs, database names, index
names, credentials, raw health payloads, vector rows, or embeddings.

## Native Source Audit

| Area | Source | Finding |
| --- | --- | --- |
| Route registration | `internal/router/router.go` | `GET /api/v1/vector-stores/types`, `GET /api/v1/vector-stores`, and `GET /api/v1/vector-stores/:id` are Viewer+; test and CRUD routes are Admin+. |
| Handler behavior | `internal/handler/vectorstore.go` | Native list/detail responses are masked but still include connection/index structure, so PA strips them. `POST /:id/test` probes the external store and may save detected version metadata for DB stores. |
| Service rules | `internal/application/service/vectorstore.go` | Create/update/delete are WeKnora-owned admin flows; delete protects stores still bound to KBs. |
| Health checks | `internal/application/service/vectorstore_healthcheck.go` | Tests reach external engines such as Postgres, Elasticsearch, Qdrant, Milvus, Weaviate, Doris, OpenSearch, or Tencent VectorDB. |
| Types | `internal/types/vectorstore.go` | `ConnectionConfig` contains sensitive host/address/credential fields; PA exposes only counts, source, engine, read-only flag, status, and safe indexes. |

## PA Surface

Endpoints:

```text
GET /api/vector-stores/native/overview?limit=10
GET /api/vector-stores/native/stores/by-index/{store_index}
POST /api/vector-stores/native/stores/by-index/{store_index}/test
```

Key behavior:

- Overview schema is `wnx-p2-04`, `masked=true`, and `management_mode=safe_read_confirmed_test`.
- Store list/detail uses PA `safe_index` links instead of raw WeKnora vector store IDs.
- Store test returns `blocked` unless the caller provides an explicit confirmation phrase.
- Confirmed tests return only `success` and `version_detected`; PA does not return native version strings or raw errors.
- CRUD, raw tests, raw config display, PA-owned vector administration, and KB rebind mutation remain backlog.

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_vector_store_management.py --browser
```

Sanitized output:

```text
WeKnora native vector store management readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- store_types: status=live count=7
- stores: status=live count=1 env=1 user=0
- store_read: live detail=live
- store_test: overview=blocked blocked_path=blocked confirmed_path=not_requested
- kb_binding: status=available source=env engine=postgres
- embedding: status=live provider=openai_compatible mock=False
- mutations: backlog
- browser: Capability Center rendered vector store management readiness
```

Browser validation:

- Chrome headless loads the Capability Center.
- The `Vector store` group renders through `/api/vector-stores/native/overview`.
- Summary fields include `store_read_status` and `store_test_status`.
- The shared frontend status strip includes `vector_store store_test=blocked`.

## Evidence Classification

| Surface | Result | Evidence |
| --- | --- | --- |
| Store types | live | Native catalog returned 7 store types. |
| Store list | live | Native list returned 1 configured env store and 0 user stores. |
| Store detail | live | PA safe-index detail path read the configured store without exposing raw ID/config. |
| Store test | blocked | Default and bad-token paths blocked before probing external vector infrastructure. Confirmed test was not requested. |
| KB binding | live | Active KB binding reports `available`, source `env`, engine `postgres`. |
| Embedding | live | PA embedding readiness is configured, provider `openai_compatible`, non-mock. |
| Mutations | backlog | CRUD, raw config/test, KB rebind, and PA-owned vector administration are not implemented in PA. |

## PASS Statement

`WNX-P2-04` passes as `live-partial`: PA can safely read native vector-store
readiness, active KB binding, embedding readiness, and per-store detail through
WeKnora native APIs, while external tests and mutations remain explicit
blocked/backlog controls. Coverage moves Vector store from `read-only` to
`live-partial`, raising the ledger from `10.25 / 15 = 68.3%` to
`10.50 / 15 = 70.0%`.
