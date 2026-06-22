# WeKnora-First Vector Store Visibility Report

> Task: `WF-P2-03`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live PA API + live WeKnora native read-only vector store visibility.

## Scope

`WF-P2-03` exposes read-only WeKnora native vector-store readiness in PA while
preserving the PA/WeKnora storage boundary. PA does not implement vector-store
CRUD, connection tests, raw connection display, KB rebind mutation, or
PA-owned vector administration in this task.

The intended PA surface is truthful status:

- list native vector-store engine type readiness
- count configured native vector stores by source
- show active KB binding status without raw store IDs
- show PA embedding readiness beside WeKnora vector-store readiness
- keep mutation and connection-test surfaces backlog
- avoid leaking connection strings, database credentials, provider tokens,
  raw health payloads, local database contents, index names, collection names,
  vector records, or screenshots

## Native Source Audit

| Area | Source | Finding |
| --- | --- | --- |
| Route registration | `internal/router/router.go` | `GET /api/v1/vector-stores/types`, `GET /api/v1/vector-stores`, and `GET /api/v1/vector-stores/:id` are Viewer+ read-only routes. CRUD and connection tests are Admin+. |
| Vector-store handler | `internal/handler/vectorstore.go` | List merges env stores and DB stores. Native responses are masked, but still contain connection/index display fields that PA strips. |
| Vector-store types | `internal/types/vectorstore.go` | Native type metadata includes field schemas and sensitive-field markers. PA surfaces only counts, engine type, and display name. |
| Store display for KBs | `internal/handler/knowledgebase.go`, `internal/application/service/vectorstore.go` | Native KB responses include safe vector store display fields such as source, engine type, and status; shared KBs suppress owner store metadata. |
| Storage boundary | `internal/types/knowledgebase.go`, vector-store service | WeKnora owns vector/chunk storage and KB binding. PA SQLite remains business state only. |

## PA API Shape

New endpoint:

```text
GET /api/vector-stores/native/overview?limit=5
```

Response categories:

- `status`: `live`, `blocked`, or `backlog`
- `store_types`: live engine type catalog count and field-count metadata
- `stores`: live vector-store count, source counts, read-only count, and engine counts
- `kb_binding`: active KB binding status, source, and engine type, without raw IDs
- `embedding`: PA model/embedding readiness, model name, mock flag, and dimension
- `mutations`: backlog list for CRUD, connection tests, raw config display, PA-owned admin, and KB rebind mutation

Frontend status strip now reads the endpoint and shows a `Vector store` chip
plus type/store/KB/embedding readiness details.

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_vector_store_visibility_live.py
```

Sanitized output:

```text
WeKnora vector store visibility smoke passed (live)
- PA endpoint: /api/vector-stores/native/overview
- overview status: live
- store types status/count: live/7
- stores status/count/env/user: live/1/1/0
- KB binding status/source/engine: available/env/postgres
- embedding status/provider/mock: live/openai_compatible/False
- mutations status: backlog
- sanitized response: True
```

Browser validation:

- The shared PA status strip loads `/api/vector-stores/native/overview`.
- The `Vector store` chip renders the live vector-store status.
- Details include vector-store type count, store count, active KB binding
  status, and embedding readiness.

## Evidence Classification

| Status | Meaning in this task |
| --- | --- |
| live | Used for PA `/api/vector-stores/native/overview`, native type catalog, native store list, active KB binding display, and embedding readiness. |
| blocked | Would apply if read-only vector-store list/type endpoints are unavailable, if KB binding cannot be queried, or if embedding is mock/unconfigured. Not observed. |
| configured_unknown | Would apply if the active KB is reachable but native vector-store display fields are absent. Not observed. |
| backlog | Vector-store CRUD, connection tests, raw config display, PA-owned admin, and KB rebind mutation remain backlog by design. |

## Safety Boundary

PA does not expose these vector-store fields:

- raw vector store ID
- tenant ID
- connection config
- index config
- endpoint, host, port, or address
- username or password
- API key or provider token
- database name
- index name
- collection name or collection prefix
- raw health payload
- vector records or embeddings
- local database contents

The report and smoke output also avoid runtime secret values, private endpoints,
service tokens, logs, caches, screenshots, and raw provider payloads.

## Storage Boundary

PA business state remains in PA's local database: documents, conversations,
tasks, outputs, citations, and history records.

WeKnora remains the authoritative owner for knowledge chunks, embeddings,
retrieval indexes, KB binding, and vector-store administration. PA only shows
sanitized readiness and binding status.

## PASS Statement

`WF-P2-03` passes for read-only native vector-store visibility. PA can now show
native vector-store type readiness, configured store counts, active KB binding,
and embedding readiness without exposing connection details or mutating native
vector-store state.

Vector-store CRUD, connection tests, raw config display, KB rebind mutation,
and PA-owned vector administration remain explicit backlog.
