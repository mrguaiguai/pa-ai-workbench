# PHASE3 WeKnora Deployment Map

> Task: P3-M1-A1
>
> Scope: audit WeKnora local / intranet deployment files only. No WeKnora source code or PA product business code is changed.

## Audited Sources

- WeKnora root README files: `README.md`, `README_CN.md`
- Docker files: `docker-compose.yml`, `docker-compose.dev.yml`
- Runtime config: `.env.example`, `config/config.yaml`
- Scripts and Make targets: `Makefile`, `scripts/start_all.sh`, `scripts/dev.sh`, `scripts/quick-dev.sh`, `scripts/check-env.sh`
- Helm: `helm/README.md`, `helm/values.yaml`, `helm/templates/*`
- Deployment docs: `docs/wiki/开发部署/快速开发模式.md`, `docs/wiki/核心功能/知识图谱.md`, `docs/wiki/核心功能/开启知识图谱功能.md`, `docs/wiki/运维排障/常见问题.md`, `docs/cloud-image/tencent-lighthouse.md`

## WeKnora Startup Modes

| Mode | Command / entry | Use in M1 | Notes |
| --- | --- | --- | --- |
| Default Docker Compose | `cp .env.example .env`, then `docker compose up -d` | Recommended local / intranet baseline | Starts frontend, app, docreader, PostgreSQL/ParadeDB, Redis. Web UI is exposed on `http://localhost` and backend API on `http://localhost:8080`. |
| Compose profiles | `docker compose --profile <name> up -d` | Enable only needed capabilities | Profiles include `neo4j`, `minio`, `langfuse`, `searxng`, `qdrant`, `milvus`, `weaviate`, `doris`, `jaeger`, `dex`, and `full`. |
| Start script | `./scripts/start_all.sh` or `make start-all` | Useful for operator startup | Creates `.env` from `.env.example` if missing and can start Docker services, Ollama, or both. |
| Development mode | `make dev-start`, `make dev-app`, `make dev-frontend` | Developer only, not M1 trial default | `docker-compose.dev.yml` starts infrastructure; app and frontend run locally. Frontend dev server uses port `5173`. |
| Quick development script | `./scripts/quick-dev.sh` | Developer convenience only | Interactive wrapper around dev infrastructure, backend, and frontend startup. It writes runtime logs and pid files, which must not be committed. |
| Helm / Kubernetes | `helm install weknora ./helm ...` | Candidate intranet cluster deployment | Requires Kubernetes 1.25+, Helm 3.10+, PVC support, and secrets for DB, Redis, and JWT. App readiness/liveness probes use `/health`. |
| Cloud image / lite | cloud-image scripts or `make run-lite` | Operational reference only for M1 | Cloud-image docs require verifying `docker compose ... ps` healthy. Lite mode is single-binary oriented and is not the default WeKnora backend reuse route for PA M1. |

## Dependency Services

| Service | Required | Deployment source | Default role |
| --- | --- | --- | --- |
| `frontend` | Yes for WeKnora UI | `docker-compose.yml`, Helm frontend | Nginx-hosted WeKnora Web UI; proxies backend traffic. |
| `app` | Yes | `docker-compose.yml`, Helm app | Go/Gin backend API, auth, RAG, Wiki, task orchestration, model calls. |
| `docreader` | Yes for document upload / parse | `docker-compose.yml`, Helm docreader | gRPC document parser for PDF, DOCX, images, Excel, Markdown, HTML, etc. |
| `postgres` / ParadeDB | Yes | `docker-compose.yml`, Helm PostgreSQL | Main relational DB plus default vector / BM25 retrieval backend when `RETRIEVE_DRIVER=postgres`. |
| `redis` | Yes | `docker-compose.yml`, Helm Redis | Stream manager and async task queue. Compose starts it with password auth but no explicit healthcheck. |
| `minio` | Optional | Compose profile `minio`, Helm `minio.enabled` | Object storage alternative to local files. Needed when M1 requires S3-compatible storage or cross-host file access. |
| `neo4j` | Optional | Compose profile `neo4j`, Helm `neo4j.enabled` | Knowledge graph / GraphRAG dependency. Requires `NEO4J_ENABLE=true` and `ENABLE_GRAPH_RAG=true` style feature configuration. |
| `qdrant` | Optional | Compose profile `qdrant`, Helm `qdrant.enabled` | Alternative vector DB via `RETRIEVE_DRIVER=qdrant`. |
| `milvus` | Optional | Compose profile `milvus` | Alternative vector DB via `RETRIEVE_DRIVER=milvus`. |
| `weaviate` | Optional | Compose profile `weaviate` | Alternative vector DB via `RETRIEVE_DRIVER=weaviate`. |
| `doris` | Optional | Compose profile `doris` | Alternative vector DB / analytical vector backend via `RETRIEVE_DRIVER=doris`. |
| `searxng` | Optional | Compose profile `searxng` / `full` | Intranet web search provider. Defaults bind to loopback unless `SEARXNG_BIND` is changed. |
| `langfuse` stack | Optional | Compose profile `langfuse`, `.env.example` | Observability for chat, embedding, rerank, VLM, ASR, Agent loops. |
| `jaeger` | Optional | Compose profile `jaeger`, Helm `jaeger.enabled` | OpenTelemetry tracing target. App env points OTLP to `jaeger:4317`. |
| `ollama` | Optional external/local | README and `scripts/start_all.sh` | Local LLM/embedding provider endpoint, default `OLLAMA_BASE_URL=http://host.docker.internal:11434`. |

## Ports

| Component | Default host port | Container / service port | Notes |
| --- | --- | --- | --- |
| Frontend Web UI | `80` via `FRONTEND_PORT` | `80` | Public WeKnora UI entry. |
| App backend API | `8080` via `APP_PORT` | `8080` | Backend API and `GET /health`. Frontend proxies to `APP_BACKEND_PORT`, default `8080`. |
| Frontend dev server | `5173` | local Vite | Development mode only. |
| DocReader gRPC | not published in production compose | `50051` | Production compose uses `expose`; dev compose maps `${DOCREADER_PORT:-50051}:50051`. |
| PostgreSQL / ParadeDB | not published in production compose; dev `5432` | `5432` | Required DB and default retrieval backend. |
| Redis | not published in production compose; dev `6379` | `6379` | Required stream/task backend. |
| MinIO | `9000`, console `9001` | `9000`, `9001` | Optional profile; do not expose with default credentials in trial LAN. |
| Langfuse Web | `3000` | `3000` | Optional tracing UI. |
| Langfuse MinIO | `9100`, console `9101` | `9000`, `9001` | Optional Langfuse internal object storage in dev/compose profile. |
| SearXNG | `8888` bound to `127.0.0.1` by default | `8080` | Only expose to LAN after rotating `SEARXNG_SECRET`. |
| Neo4j | `7474`, `7687` | `7474`, `7687` | Browser and Bolt ports for GraphRAG / knowledge graph. |
| Qdrant | `6333`, `6334` | `6333`, `6334` | REST and gRPC. |
| Milvus | `19530`, health `9091` | `19530`, `9091` | Optional vector DB profile. |
| Weaviate | `9035`, `50052` | `8080`, `50051` | Optional vector DB profile. |
| Doris | FE HTTP `8030`, FE MySQL `9030`, BE HTTP `8040` | `8030`, `9030`, `8040` | Optional vector backend profile. |
| Jaeger | `16686`, `4317`, `4318`, plus collector ports | same | Optional tracing profile. |
| Dex | `5556` | `5556` | Optional OIDC development service. |

## Necessary Environment Variables

M1 operators must create `.env` from `.env.example` and replace defaults before using real or pilot data. Keep `.env` untracked.

| Area | Variables | M1 notes |
| --- | --- | --- |
| Runtime | `GIN_MODE`, `LOG_LEVEL`, `TZ`, `WEKNORA_LANGUAGE`, `DISABLE_REGISTRATION` | Use `GIN_MODE=release`; disable open registration for shared intranet trials. |
| Backend routing | `APP_HOST`, `APP_PORT`, `APP_BACKEND_PORT`, `APP_SCHEME`, `APP_EXTERNAL_URL`, `FRONTEND_PORT` | `APP_EXTERNAL_URL` matters for IM/file links; internal service names differ from host ports. |
| Database | `DB_DRIVER`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Production compose overrides host to `postgres`; dev/local app uses host ports. |
| Redis | `REDIS_ADDR`, `REDIS_USERNAME`, `REDIS_PASSWORD`, `REDIS_DB`, `REDIS_PREFIX`, `STREAM_MANAGER_TYPE` | `STREAM_MANAGER_TYPE=redis` is the expected non-mock async path. |
| Retrieval | `RETRIEVE_DRIVER`, plus driver-specific vars such as `QDRANT_*`, `MILVUS_*`, `WEAVIATE_*`, `DORIS_*`, `ELASTICSEARCH_*`, `TENCENT_VECTORDB_*` | Default is `postgres`; non-default drivers require matching service/profile and model dimensions. |
| Storage | `STORAGE_TYPE`, `LOCAL_STORAGE_BASE_DIR`, `MINIO_*`, `COS_*`, `TOS_*`, `S3_*`, `OBS_*`, `STORAGE_ALLOW_LIST` | Local storage uses `/data/files`; object storage must be reachable from clients that consume file URLs. |
| DocReader | `DOCREADER_ADDR`, `DOCREADER_TRANSPORT`, `DOCREADER_PORT`, `MAX_FILE_SIZE_MB`, `WEKNORA_DOCREADER_CALL_TIMEOUT`, `DOCREADER_*_WORKERS` | Production default is `docreader:50051`; enabling large uploads requires synchronized restart across frontend, app, docreader, and browser bundle. |
| gRPC security | `GRPC_TLS_ENABLED`, `GRPC_TLS_CERT`, `GRPC_TLS_KEY`, `GRPC_TLS_CA`, `GRPC_TLS_SERVER_NAME`, `GRPC_AUTH_TOKEN` | For M1 LAN, prefer TLS plus token if docreader crosses host or trust boundaries. |
| Models | Built-in model placeholders such as `LLM_MODEL_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `RERANK_*`, `OLLAMA_BASE_URL` | RAG and Wiki are not useful until LLM and embedding models are configured and verified. Never commit API keys. |
| Security | `JWT_SECRET`, `TENANT_AES_KEY`, `SYSTEM_AES_KEY`, `CRYPTO_MASTER_KEY`, `CRYPTO_SALT`, `WEKNORA_TENANT_ENABLE_RBAC`, `WEKNORA_BOOTSTRAP_SYSTEM_ADMIN_EMAIL` | `.env.example` contains demonstration values; rotate before M1. Losing AES keys can make encrypted credentials unrecoverable. |
| GraphRAG | `ENABLE_GRAPH_RAG`, `NEO4J_ENABLE`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | Requires Neo4j profile/service and knowledge-base entity/relation extraction settings. |
| Observability | `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_*`, OTEL env in compose | Optional but useful for M1 diagnostics; rotate default Langfuse self-host secrets. |
| PA Adapter trial | `KNOWLEDGE_BACKEND=weknora_api`, `MOCK_MODE=false`, `WEKNORA_BASE_URL`, `WEKNORA_SERVICE_TOKEN`, `WEKNORA_TIMEOUT_SECONDS`, `WEKNORA_WORKSPACE_ID`, `WEKNORA_DEFAULT_KB_ID` | These belong to PA AI Workbench runtime, not WeKnora upstream. They are required for PA M1 to use WeKnora as RAG/Wiki fact source. |

## Health Checks

| Target | health check | Source |
| --- | --- | --- |
| App container | `curl -f http://localhost:8080/health` | `docker-compose.yml` app healthcheck |
| App HTTP from host | `curl http://localhost:8080/health` | WeKnora router exposes unauthenticated `/health` returning `{"status":"ok"}` |
| Frontend dependency | waits for app `service_healthy` | `docker-compose.yml` frontend `depends_on` |
| DocReader | `grpc_health_probe -addr=localhost:50051` | Compose docreader healthcheck |
| PostgreSQL | `pg_isready -U ${DB_USER}` | Compose and dev compose healthcheck |
| MinIO | `curl -f http://localhost:9000/minio/health/live` | Compose profile healthcheck |
| Milvus | `curl -f http://localhost:9091/healthz` | Compose profile healthcheck |
| Langfuse ClickHouse | `wget ... http://localhost:8123/ping` | Dev/compose Langfuse profile |
| Helm app | liveness/readiness HTTP GET `/health` on service port `8080` | `helm/values.yaml` |
| Cloud image | `docker compose -f /opt/WeKnora/docker-compose.yml ps` all healthy | `docs/cloud-image/tencent-lighthouse.md` |

Redis has no explicit Compose healthcheck in the audited files. Treat `docker compose ps`, app logs, and task processing behavior as required supplemental checks.

## RAG / Wiki Capability Dependencies

- RAG requires the app backend, database, Redis task queue, docreader, storage backend, an embedding model, and a retrieval driver with matching vector dimensions.
- Default retrieval uses PostgreSQL/ParadeDB through `RETRIEVE_DRIVER=postgres`; switching to Qdrant, Milvus, Weaviate, Doris, Elasticsearch, or Tencent VectorDB requires both environment variables and the corresponding service/profile or reachable external endpoint.
- Document upload and indexing require docreader gRPC to be healthy; large or complex PDF/DOCX/image imports depend on docreader worker limits, file-size limits, and timeout settings.
- Wiki Mode depends on successful document ingestion, LLM generation, Redis-backed async tasks, database migrations for wiki tables, and the configured retrieval/indexing backend.
- Wiki ingest at larger scale uses task queue / DLQ behavior; M1 must verify indexing status and failure surfaces instead of assuming upload success equals searchable evidence.
- GraphRAG / knowledge graph is optional but depends on Neo4j, `NEO4J_ENABLE=true`, `ENABLE_GRAPH_RAG=true`, and per-knowledge-base entity/relation extraction settings.
- Langfuse and Jaeger are diagnostic dependencies, not RAG/Wiki correctness dependencies, but they materially reduce M1 triage risk.

## M1 Intranet Pilot Risks

| risk | Why it matters | Mitigation |
| --- | --- | --- |
| Default demo secrets in `.env.example` | Example DB, Redis, JWT, AES, Langfuse, MinIO, Neo4j, and SearXNG values are not suitable for a shared intranet. | Generate fresh secrets before trial; never commit `.env`; prefer secret manager or Helm existingSecret in Kubernetes. |
| Model / embedding not configured | Upload may complete while retrieval quality is unusable, or document processing may fail with model errors. | Complete P3-M1-A2 before adapter E2E; verify one upload, one retrieval, and one Wiki draft with real evidence. |
| External model endpoint unavailable from LAN | Ollama or cloud model base URLs may not be reachable from containers. | Validate container-to-model connectivity, not just host connectivity; configure `OLLAMA_BASE_URL` or model `BASE_URL` accordingly. |
| DocReader gRPC security disabled by default | Production compose keeps docreader internal, but cross-host or cluster deployments may expose gRPC without TLS/token. | Keep docreader internal; if exposed, enable TLS plus `GRPC_AUTH_TOKEN`. |
| Redis has no explicit compose healthcheck | App may start while task queue is partially unavailable; RAG/Wiki indexing depends on async tasks. | Add operational smoke checks around upload/index status and inspect app/Redis logs during M1. |
| Optional profile mismatch | Enabling `RETRIEVE_DRIVER=qdrant` or GraphRAG without starting Qdrant/Neo4j causes runtime failures. | Align `.env` with `docker compose --profile ...` or external endpoints; document profile set per environment. |
| Port collisions on shared hosts | Ports `80`, `8080`, `5432`, `6379`, `3000`, `7474`, `7687`, `9000`, `9001`, `8888` commonly collide. | Reserve host ports or override env vars before launch; publish only required services. |
| Upload-size limit split across layers | `MAX_FILE_SIZE_MB` affects frontend Nginx, app, docreader, and browser bundle at startup only. | Set before container build/start and restart all relevant layers together. |
| Local file URLs / object storage reachability | IM clients or PA frontends may not resolve container-only hosts such as `minio:9000`. | Use reachable `APP_EXTERNAL_URL` / object storage endpoint for intranet clients. |
| AES key loss | Helm can generate AES keys; deleting secrets can make encrypted credentials unrecoverable. | Persist `TENANT_AES_KEY` and `SYSTEM_AES_KEY` explicitly in M1 environment records. |
| Real data leakage into git | Volumes, uploads, logs, `.env`, node_modules, and dist artifacts are present or ignored in the PA repo. | Stage only task docs/spec files; run `git status --ignored --short`; do not add ignored runtime paths. |
| WeKnora raw API dependency creep | PA M1 must not let frontend or Agent depend directly on WeKnora raw responses. | Keep WeKnora access behind PA `KnowledgeBackend Adapter`; use `KNOWLEDGE_BACKEND=weknora_api` and `MOCK_MODE=false` for M1 validation. |

## M1 Recommended Baseline

For the first PA intranet trial, use default Docker Compose plus only the profiles actually needed:

```bash
cp .env.example .env
# edit .env: rotate secrets, configure models, storage, retrieval, docreader, and RBAC
docker compose up -d
curl http://localhost:8080/health
docker compose ps
```

Then configure PA AI Workbench with:

```text
KNOWLEDGE_BACKEND=weknora_api
MOCK_MODE=false
WEKNORA_BASE_URL=http://<weknora-host>:8080
WEKNORA_SERVICE_TOKEN=<service-token-from-secure-env>
WEKNORA_TIMEOUT_SECONDS=60
WEKNORA_WORKSPACE_ID=<workspace-id>
WEKNORA_DEFAULT_KB_ID=<knowledge-base-id>
```

Do not commit the concrete token, workspace id, knowledge-base id, `.env`, uploads, database files, logs, `dist`, `node_modules`, or real pilot documents.
