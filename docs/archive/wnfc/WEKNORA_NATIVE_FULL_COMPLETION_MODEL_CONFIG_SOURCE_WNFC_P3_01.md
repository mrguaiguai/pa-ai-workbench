# WNFC-P3-01 Product-Grade Model Config Source Evidence

Task: WNFC-P3-01
Date: 2026-06-24
Decision: PASS
Evidence type: live api plus native go test plus docker runtime

## Scope

WNFC-P3-01 requires WeKnora product-grade model configuration to become the
source of truth through `config/builtin_models.yaml` or
`BUILTIN_MODELS_CONFIG`, with the PA env bridge aligned to that native source.

This task is now complete for the product-grade config source slice:

- WeKnora native runtime loads `config/builtin_models.yaml`.
- Native `/api/v1/models` exposes YAML-managed built-in model ownership through
  non-secret `managed_by="yaml"` metadata.
- PA `/api/model/native/overview` proves YAML source-of-truth and PA bridge
  alignment.
- Qwen `qwen3-rerank` is configured as the native YAML-managed rerank model and
  passes the native active rerank check.

## Native Source Audit

Native WeKnora already had the declarative model loader:

- `config/builtin_models.yaml.example`
  - documents the expected `builtin_models` shape for `KnowledgeQA`,
    `Embedding`, and `Rerank` model entries.
- `docs/BUILTIN_MODELS.md`
  - states the recommended path is `config/builtin_models.yaml`, with
    `BUILTIN_MODELS_CONFIG` as the override.
- `internal/container/container.go`
  - runs `types.LoadBuiltinModelsConfig(...)` after migrations.
- `internal/types/builtin_models_config.go`
  - reads the YAML path, interpolates env vars, UPSERTs models, tags YAML
    lifecycle ownership with `managed_by="yaml"`, and prunes only YAML-managed
    rows.
- `internal/types/model.go`
  - defines `IsBuiltin` and `ManagedBy` on native model rows.
- `internal/models/rerank/aliyun_reranker.go`
  - previously supported only the legacy DashScope text-rerank
    `input/parameters/output` protocol. Qwen `qwen3-rerank` uses the newer
    compatible API with top-level `query`, `documents`, `top_n`, and `results`.

PA-only work would have produced a fake green state: PA could mark env values as
configured, but native WeKnora would still fail to prove YAML ownership and
would call the wrong DashScope protocol for `qwen3-rerank`.

## Changes

Native changes:

- `internal/handler/dto/model.go`
  - Adds non-secret `managed_by` lifecycle metadata to model API responses.
- `internal/handler/dto/model_test.go`
  - Verifies built-in model responses still strip tenant config and secrets
    while exposing `managed_by="yaml"`.
- `internal/models/rerank/aliyun_reranker.go`
  - Adds a `qwen3-rerank` compatible API path.
  - Normalizes `https://dashscope.aliyuncs.com/compatible-api/v1` to
    `/compatible-api/v1/reranks`.
  - Keeps legacy `gte-rerank-v2` / DashScope text-rerank behavior unchanged.
- `internal/models/rerank/aliyun_reranker_test.go`
  - Covers both Qwen3 compatible protocol and legacy DashScope protocol.
- `config/builtin_models.yaml`
  - Adds YAML-managed `KnowledgeQA`, `Embedding`, and `Rerank` entries using
    env references only.
- `docker-compose.yml`
  - Mounts `./config/builtin_models.yaml` into the app container.

PA changes:

- `knowledge_engine/backends/weknora_api_backend.py`
  - Preserves `managed_by` in the PA-safe native model summary.
- `backend/app/services/model_status_service.py`
  - Marks `/api/model/status` as the current `pa_env_bridge`.
- `backend/app/services/model_config_service.py`
  - Adds `config_source` and `pa_bridge_alignment` surfaces to
    `/api/model/native/overview`.
- `backend/app/services/native_status_service.py`
  - Mirrors `config_source_status`, `yaml_managed_model_count`, and
    `pa_bridge_alignment_status` in the status center summary.
- `backend/scripts/check_weknora_native_model_config_source.py`
  - Proves current runtime YAML source-of-truth through PA.
- `backend/scripts/check_weknora_native_qwen3_rerank_active.py`
  - Calls native `/api/v1/initialization/rerank/check` with local
    Qwen/DashScope config and prints only sanitized availability metadata.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this report to the WNFC evidence inventory.

Local ignored config:

- The outer `.env` was updated locally with chat/embedding bridge keys and
  Qwen rerank keys. It is ignored by Git and must not be staged.

## Validation Evidence

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  backend/app/services/model_config_service.py \
  backend/app/services/model_status_service.py \
  backend/app/services/native_status_service.py \
  backend/app/schemas.py \
  knowledge_engine/backends/weknora_api_backend.py \
  backend/scripts/check_weknora_native_model_config_source.py \
  backend/scripts/check_weknora_native_qwen3_rerank_active.py \
  backend/scripts/check_weknora_native_full_completion_acceptance.py
```

Result: PASS.

Native Go tests:

```bash
docker run --rm \
  -v /Users/mac/Downloads/WeKnora-main:/workspace \
  -w /workspace \
  golang:1.26.0 \
  go test ./internal/models/rerank

docker run --rm \
  -v /Users/mac/Downloads/WeKnora-main:/workspace \
  -w /workspace \
  golang:1.26.0 \
  go test ./internal/handler/dto
```

Result: PASS.

Docker/runtime validation:

```bash
docker compose build app
docker compose up -d app
```

Result: PASS. The app image rebuilt successfully, the `WeKnora-app` container
was recreated, and `http://127.0.0.1:8080/health` returned healthy.

Live PA/WeKnora source-of-truth smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_model_config_source.py
```

Current-run output:

```text
WeKnora native product-grade model config source
- decision: PASS
- evidence_type: live api
- config_source: status=live yaml_managed=3 missing_required=none
- pa_bridge_alignment: status=live bridge_status=live
- catalog: models=5 yaml_managed=3
```

Live native Qwen rerank active check:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_qwen3_rerank_active.py
```

Current-run output:

```text
qwen3_rerank_check
available=true
message=重排功能正常，返回1个结果
```

## Sensitive Data Handling

- No API key, service token, raw provider payload, or request body is present in
  this report.
- `config/builtin_models.yaml` contains env references only.
- The real Qwen/DashScope key is local-only in ignored `.env`.
- The active rerank smoke prints only `available` and a bounded message.

## Status Impact

WNFC-P3-01 is `[x]` complete.

Model/embedding/rerank/parser still remains an overall WNFC work area because
WNFC-P3-02 and WNFC-P3-03 must separately prove active chat/embedding/rerank,
parser, and storage diagnostics. Aggregate WNFC score remains
`11.50 / 14 = 82.1%` until those task rows complete.
