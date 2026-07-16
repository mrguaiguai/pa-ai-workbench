# WNFC-P3-02 Model, Embedding, And Rerank Active Tests Evidence

Task: WNFC-P3-02
Date: 2026-06-24
Decision: PASS
Evidence type: live api

## Scope

WNFC-P3-02 requires real active tests for model, embedding, and rerank
providers. A configured-but-untested provider is not enough for this task.

This task is complete for the active-test diagnostics slice:

- Native chat model active check returns `available=true`.
- Native embedding active check returns `available=true` and a real
  1024-dimensional vector.
- Native rerank active check returns `available=true` and at least one rerank
  result.
- The PA smoke output is sanitized and does not print API keys, service tokens,
  request bodies, or provider payloads.

## Native Source Audit

The active-test path is native WeKnora, not a PA mock:

- `internal/router/router.go`
  - exposes Admin-only native active-test endpoints:
    - `POST /api/v1/initialization/remote/check`
    - `POST /api/v1/initialization/embedding/test`
    - `POST /api/v1/initialization/rerank/check`
- `internal/handler/initialization.go`
  - defines `ModelTestRequest`.
  - validates model name, base URL, and SSRF rules where applicable.
  - builds temporary native model objects through `buildTestModel`.
  - runs chat through `chat.ConfigFromModel -> chat.NewChat -> Chat`.
  - runs embedding through `embedding.ConfigFromModel -> embedding.NewEmbedder -> Embed`.
  - runs rerank through `rerank.ConfigFromModel -> rerank.NewReranker -> Rerank`.
- `internal/models/rerank/aliyun_reranker.go`
  - now supports the Qwen `qwen3-rerank` compatible API path validated in
    WNFC-P3-01.

PA-only status checks would be insufficient because `/api/model/status` can
prove configuration presence but cannot prove live upstream chat, embedding, or
rerank execution. WNFC-P3-02 therefore uses PA automation to call the native
active-test APIs with real local provider configuration and sanitized output.

## Changes

PA changes:

- `backend/scripts/check_weknora_native_model_embedding_rerank_active.py`
  - Calls all three native active-test endpoints.
  - Reads real local provider config from ignored env files and process env.
  - Prints only `available`, embedding `dimension`, bounded messages, and
    missing-field diagnostics.
  - Returns non-zero for incomplete config or any failed active test.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this report to the WNFC evidence inventory.

No UI file was touched, so no browser evidence is required for this task.
No native Go file was changed in WNFC-P3-02, so no new Go test is required for
this task. The native rerank Go tests for the P3-01 Qwen path remain the
runtime prerequisite for the rerank active check.

## Validation Evidence

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  backend/scripts/check_weknora_native_model_embedding_rerank_active.py \
  backend/scripts/check_weknora_native_full_completion_acceptance.py
```

Result: PASS.

Live PA/WeKnora active-test smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_model_embedding_rerank_active.py
```

Current-run output:

```text
WeKnora native model/embedding/rerank active tests
- decision: PASS
- evidence_type: live api
- chat: available=true message=连接正常，模型可用
- embedding: available=true dimension=1024 message=测试成功，向量维度=1024
- rerank: available=true message=重排功能正常，返回1个结果
- output: sanitized
```

WNFC acceptance checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_full_completion_acceptance.py
```

Result: PASS in in-progress mode.

Diff hygiene:

```bash
git diff --check
```

Result: PASS in the PA workbench repository and the outer WeKnora repository.

## Sensitive Data Handling

- No API key, service token, raw provider payload, or request body is present in
  this report.
- The active-test script redacts secret-shaped tokens in messages before
  printing.
- Real provider credentials remain local-only in ignored `.env` files.
- The task does not close WNFC-P1-01; credential-bearing Notion/Yuque/Feishu
  connector setup remains blocked until those real third-party credentials and
  workspaces are supplied.

## Status Impact

WNFC-P3-02 is `[x]` complete.

Model/embedding/rerank/parser remains an overall WNFC work area because
WNFC-P3-03 must still prove parser and storage diagnostics. Aggregate WNFC
score remains `11.50 / 14 = 82.1%` until the broader scored group reaches
full-complete.
