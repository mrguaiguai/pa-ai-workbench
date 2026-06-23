# PHASE3 WeKnora RAG / Wiki Config Checklist

> Task: P3-M1-A2
>
> Purpose: give M1 intranet operators a configuration checklist for deciding whether a WeKnora environment can support real RAG / Wiki instead of mock or partial paths.
>
> Guardrail: record variable names, checks, and placeholders only. Do not write real API keys, tokens, workspace IDs, knowledge-base IDs, pilot documents, uploads, logs, or database dumps.

## Audited Sources

- `config/builtin_models.yaml.example`
- `.env.example`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `helm/values.yaml`
- `docs/BUILTIN_MODELS.md`
- `docs/QA.md`
- `docs/api/model.md`
- `docs/api/system.md`
- `docs/wiki/集成扩展/集成向量数据库.md`
- `docreader/README.md`
- `docreader/config.py`
- `pa-ai-workbench/docs/PHASE3_WEKNORA_DEPLOYMENT_MAP.md`

## Required M1 Configuration

| Area | Required for real RAG / Wiki | Key variables / config | Readiness check |
| --- | --- | --- | --- |
| LLM | Yes | `config/builtin_models.yaml`, `LLM_MODEL_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_PROVIDER`, or UI/API-created `KnowledgeQA` model | A default or selected `KnowledgeQA` model exists; provider endpoint is reachable from the `app` container; no literal `${ENV}` placeholder remains in model config. |
| Embedding | Yes | `EMBEDDING_MODEL_NAME`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_PROVIDER`, `embedding_parameters.dimension` | Embedding model exists and returns vectors; dimension matches the selected vector store schema/collection/table. |
| vector store | Yes | `RETRIEVE_DRIVER`, plus driver-specific env such as `QDRANT_*`, `MILVUS_*`, `WEAVIATE_*`, `DORIS_*`, `ELASTICSEARCH_*`, `OPENSEARCH_*`, `TENCENT_VECTORDB_*` | Selected driver is registered, service/profile or external endpoint is reachable, and a test document can write chunk vectors. |
| PostgreSQL / ParadeDB | Yes | `DB_DRIVER`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | `postgres` service is healthy; migrations complete; app logs do not show database connection or migration errors. |
| Redis | Yes | `STREAM_MANAGER_TYPE`, `REDIS_ADDR`, `REDIS_USERNAME`, `REDIS_PASSWORD`, `REDIS_DB`, `REDIS_PREFIX` | Async upload/index tasks progress from queued/processing to terminal status; no Redis timeout errors in app logs. |
| DocReader | Yes | `DOCREADER_ADDR`, `DOCREADER_TRANSPORT`, `DOCREADER_PORT`, `MAX_FILE_SIZE_MB`, `WEKNORA_DOCREADER_CALL_TIMEOUT`, `DOCREADER_*` worker limits | `grpc_health_probe` succeeds; `/api/v1/system/parser-engines` reports docreader available; a PDF/DOCX/Markdown file parses successfully. |
| storage | Yes | `STORAGE_TYPE`, `LOCAL_STORAGE_BASE_DIR`, or object storage variables such as `MINIO_*`, `COS_*`, `TOS_*`, `S3_*`, `OBS_*` | Upload files and generated images are readable by WeKnora and by the intended intranet clients. |
| Auth / secrets | Yes | `JWT_SECRET`, `TENANT_AES_KEY`, `SYSTEM_AES_KEY`, `CRYPTO_MASTER_KEY`, `CRYPTO_SALT`, `WEKNORA_TENANT_ENABLE_RBAC`, `WEKNORA_BOOTSTRAP_SYSTEM_ADMIN_EMAIL` | Defaults are rotated; encrypted credentials remain readable across restart; registration/RBAC policy matches the M1 pilot. |
| PA adapter handoff | Yes for PA M1 | `KNOWLEDGE_BACKEND`, `MOCK_MODE`, `WEKNORA_BASE_URL`, `WEKNORA_SERVICE_TOKEN`, `WEKNORA_TIMEOUT_SECONDS`, `WEKNORA_WORKSPACE_ID`, `WEKNORA_DEFAULT_KB_ID` | PA will use `KNOWLEDGE_BACKEND=weknora_api` and `MOCK_MODE=false`; values stay in PA runtime env only, not in this checklist. |

## Optional Capability Configuration

| Area | When needed | Key variables / config | Readiness check |
| --- | --- | --- | --- |
| Rerank | Better retrieval quality / hybrid ranking | `RERANK_MODEL_NAME`, `RERANK_BASE_URL`, `RERANK_API_KEY`, `RERANK_PROVIDER`, or a `Rerank` model row | Rerank model check succeeds; retrieval logs show rerank stage without provider errors. |
| VLM / multimodal | Image/scanned PDF understanding | `VLLM` model config, knowledge-base `vlm_config`, model API `base_url` / `api_key` | Image upload is not filtered by UI; VLM call succeeds; generated image descriptions appear in document processing output. |
| ASR | Audio upload/transcription | `ASR` model config, knowledge-base `asr_config` | `/initialization/asr/check` succeeds; audio upload no longer fails with missing ASR model. |
| GraphRAG / Neo4j | Knowledge graph retrieval | `ENABLE_GRAPH_RAG`, `NEO4J_ENABLE`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`; compose profile `neo4j` | Neo4j is reachable; entity/relation extraction is enabled on the knowledge base; graph queries return nodes. |
| Langfuse | Model / Agent observability | `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_*` | Langfuse receives chat, embedding, rerank, VLM, or ASR traces; no default self-host secrets remain. |
| Jaeger / OTEL | Infrastructure tracing | Compose profile `jaeger`; OTEL env from `docker-compose.yml` | Jaeger UI shows app traces when enabled. |
| SearXNG / web search | Intranet search provider | `SEARXNG_PORT`, `SEARXNG_BIND`, `SEARXNG_SECRET`, `SSRF_WHITELIST` | Search provider endpoint is reachable and secret is rotated before LAN exposure. |

## Vector Store Checklist

| Driver | Required config | Service/profile | M1 notes |
| --- | --- | --- | --- |
| `postgres` | `RETRIEVE_DRIVER=postgres`, DB variables | Built-in `postgres` service | Recommended baseline. Uses PostgreSQL/ParadeDB and pgvector/BM25-style retrieval path. |
| `qdrant` | `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`, `QDRANT_API_KEY`, `QDRANT_USE_TLS` | `docker compose --profile qdrant up -d` or external Qdrant | Verify gRPC port `6334`; collection must match embedding dimension. |
| `milvus` | `MILVUS_ADDRESS`, `MILVUS_COLLECTION`, `MILVUS_METRIC_TYPE`, optional username/password/db | `docker compose --profile milvus up -d` or external Milvus | Metric type changes require rebuilding collection. |
| `weaviate` | `WEAVIATE_HOST`, `WEAVIATE_GRPC_ADDRESS`, `WEAVIATE_SCHEME`, `WEAVIATE_AUTH_ENABLED`, `WEAVIATE_API_KEY`, optional collection | `docker compose --profile weaviate up -d` or external Weaviate | Container access should use service names, not host-mapped localhost. |
| `doris` | `DORIS_ADDR`, `DORIS_HTTP_PORT`, `DORIS_DATABASE`, `DORIS_USERNAME`, `DORIS_PASSWORD`, `DORIS_TABLE_PREFIX`, `DORIS_COMPAT_MODE` | `docker compose --profile doris up -d` | Requires database creation and per-dimension physical tables. |
| `elasticsearch_v7` / `elasticsearch_v8` | `ELASTICSEARCH_ADDR`, `ELASTICSEARCH_USERNAME`, `ELASTICSEARCH_PASSWORD`, `ELASTICSEARCH_INDEX` | External or separately managed service | Confirm version/driver pairing and index availability. |
| `opensearch` | `OPENSEARCH_ADDR`, `OPENSEARCH_USERNAME`, `OPENSEARCH_PASSWORD`, `OPENSEARCH_INDEX`, `OPENSEARCH_INSECURE_SKIP_VERIFY` | Dev profile `opensearch` or external secured cluster | Single-node dev clusters may report yellow health because replicas are unassigned. |
| `tencent_vectordb` | `TENCENT_VECTORDB_ADDR`, `TENCENT_VECTORDB_USERNAME`, `TENCENT_VECTORDB_API_KEY`, `TENCENT_VECTORDB_DATABASE`, `TENCENT_VECTORDB_COLLECTION` | External Tencent VectorDB | Collection prefix expands by embedding dimension; sparse vector index is needed for keyword retrieval. |

## DocReader Checklist

| Check | Variables / endpoint | Expected M1 result |
| --- | --- | --- |
| gRPC endpoint | `DOCREADER_ADDR=docreader:50051`, `DOCREADER_TRANSPORT=grpc` | App can call docreader over the compose network. |
| Health probe | `grpc_health_probe -addr=localhost:50051` inside service context | Healthy before app begins document indexing. |
| File-size alignment | `MAX_FILE_SIZE_MB`, `DOCREADER_GRPC_MAX_FILE_SIZE_MB` | Same deployment limit is reflected across frontend Nginx, app, docreader, and browser bundle after restart. |
| Parser worker limits | `DOCREADER_MARKITDOWN_MAX_WORKERS`, `DOCREADER_PDF_RENDER_MAX_WORKERS`, `DOCREADER_PDF_RENDER_DPI`, `DOCREADER_PDF_JPEG_QUALITY` | Values fit pilot hardware; large PDF parsing does not starve the task queue. |
| Timeout | `WEKNORA_DOCREADER_CALL_TIMEOUT`, `WEKNORA_DOCUMENT_PROCESS_TIMEOUT` | DocReader timeout is shorter than document process timeout. |
| DOCX cap | `DOCREADER_DOCX_MAX_PAGES` | Optional cap documented when very large Word files are expected. |
| TLS / token | `GRPC_TLS_ENABLED`, `GRPC_TLS_CERT`, `GRPC_TLS_KEY`, `GRPC_TLS_CA`, `GRPC_TLS_SERVER_NAME`, `GRPC_AUTH_TOKEN` | Required if docreader crosses host/network trust boundary; optional only for internal compose network. |
| Parser status API | `/api/v1/system/parser-engines`, `/api/v1/system/parser-engines/check`, `/api/v1/system/docreader/reconnect` | Operator can confirm availability and reconnect without editing code. |

## Storage Checklist

| Storage type | Variables | M1 readiness |
| --- | --- | --- |
| `local` | `STORAGE_TYPE=local`, `LOCAL_STORAGE_BASE_DIR=/data/files` | Good for single-node pilot; verify volume persistence and file URL behavior. |
| `minio` | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY_ID`, `MINIO_SECRET_ACCESS_KEY`, `MINIO_BUCKET_NAME`, optional public endpoint | Bucket exists or auto-creates; endpoint is reachable by intranet clients that need file/image URLs. |
| `cos` | `COS_SECRET_ID`, `COS_SECRET_KEY`, `COS_REGION`, `COS_BUCKET_NAME`, `COS_APP_ID`, `COS_PATH_PREFIX` | Credentials are stored outside git and encrypted at rest. |
| `tos` / `s3` / `obs` | Provider endpoint, region, access key, secret key, bucket, path prefix | Endpoint is reachable from app/docreader and from clients consuming generated links. |

## Missing Items Decision Table

Use this table during M1 environment review. Mark each row as `configured`, `to-confirm`, `missing`, or `n/a`.

| Item | Status | Blocks real RAG? | Blocks Wiki? | Notes |
| --- | --- | --- | --- | --- |
| App `/health` works | to-confirm | Yes | Yes | `curl http://<host>:8080/health` should return ok. |
| DB migrations complete | to-confirm | Yes | Yes | Check app logs and `/system/info`. |
| Redis task queue works | to-confirm | Yes | Yes | Upload/index tasks must finish. |
| LLM configured | to-confirm | Partial | Yes | Wiki draft/publish needs generation. |
| Embedding configured with dimension | to-confirm | Yes | Yes | Dimension must match vector store. |
| vector store reachable | to-confirm | Yes | Yes | Document chunks must be searchable. |
| DocReader healthy | to-confirm | Yes | Yes | Upload parse fails otherwise. |
| Storage readable | to-confirm | Yes | Yes | Local or object storage must persist files/images. |
| Rerank configured | n/a | No | No | Quality improvement, not baseline blocker. |
| VLM configured | n/a | Only multimodal | Only multimodal | Required for image-heavy or scanned documents. |
| ASR configured | n/a | Only audio | Only audio | Required for audio ingestion. |
| Neo4j / GraphRAG configured | n/a | No | No | Required only when graph retrieval is in M1 scope. |
| PA Adapter env configured | to-confirm | Yes for PA | Yes for PA | `KNOWLEDGE_BACKEND=weknora_api`, `MOCK_MODE=false`; do not record secrets here. |

If any row marked as blocking is `missing`, the environment is not ready for real RAG / Wiki M1 acceptance.

## RAG / Wiki Acceptance Path

1. Model layer: create or load `KnowledgeQA` and `Embedding` models, then confirm model provider checks pass.
2. Infrastructure layer: confirm PostgreSQL, Redis, selected vector store, storage, and DocReader are healthy.
3. Document path: upload a small Markdown/PDF/DOCX test file; confirm parse, chunk, embedding, and vector write complete.
4. Retrieval path: ask a knowledge-base question and confirm response includes real evidence/chunks, not mock text.
5. Wiki path: generate a Wiki draft from evidence, publish/index it, then confirm later retrieval can cite the Wiki page.
6. PA path: PA AI Workbench points to WeKnora through the KnowledgeBackend Adapter with `MOCK_MODE=false`; frontend and Agent never consume raw WeKnora response fields directly.

## Environment Differences

| Environment | Difference | Checklist adjustment |
| --- | --- | --- |
| Docker Compose | Services use compose DNS names such as `postgres`, `redis`, `docreader`, `qdrant`, `minio`. | Prefer service names in env; host ports are for operator/browser access only. |
| Local development | App/frontend run on host; infra runs in `docker-compose.dev.yml`. | Use localhost host-mapped ports for DB/Redis/DocReader/vector stores; do not treat this as M1 acceptance. |
| Helm / Kubernetes | Secrets and PVCs replace `.env` and compose volumes. | Use `secrets.existingSecret` or explicit Helm secret values; make AES keys persistent across upgrades. |
| External model service | Model endpoint may be inside LAN, public cloud, Ollama, or GPUStack. | Test from the app container or pod, not only from the operator laptop. |
| External vector store | Driver config points outside compose. | Confirm network ACL, TLS/auth, index/collection/table creation, and embedding dimension compatibility. |
| Offline / intranet-only | Public model APIs and image registries may be unavailable. | Pre-pull images, use local model endpoints, mirror packages/images, and avoid docs that assume public Internet. |

## Sensitive Data Rules

- Never commit `.env`, `config/builtin_models.yaml` with real secrets, API keys, uploads, database files, logs, `dist`, `node_modules`, or pilot documents.
- Use placeholder variable names only: for example `LLM_API_KEY`, `EMBEDDING_API_KEY`, `WEKNORA_SERVICE_TOKEN`.
- If a checklist reviewer finds real credentials in a repo-tracked file, stop before commit and rotate the credential.
