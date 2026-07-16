# WeKnora Native Model/Config Live Report

> Task: `WNX-P2-01`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P2-01` is PASS for the model, embedding, rerank, and parser readiness
slice at `live-partial`.

PA now exposes a masked native model/config overview that reads WeKnora model
providers, saved model catalog metadata, parser engine readiness, storage
engine readiness, and PA chat/embedding runtime posture. Admin-only remote test
surfaces stay visibly blocked because they can use stored credentials or trigger
external probes.

This PASS does not upgrade the capability to `live-full`. The stage target for
`Model/embedding/rerank/parser` is already `live-partial`, and this task keeps
that boundary intact.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| WeKnora Native Adapter | `knowledge_engine/backends/weknora_api_backend.py` | Adds safe wrappers for model providers, model list, parser engines, and storage engine status. |
| PA Backend BFF | `/api/model/native/overview` | Returns masked counts/status for provider catalog, model catalog, parser engines, storage engines, PA runtime, and Admin-only test blockers. |
| PA Status Center | `/api/native/status` | Points the model/config capability group to `/api/model/native/overview` and marks it `partial`. |
| PA Frontend Shell | Capability Center | Renders model/config readiness from the status center without new static data. |
| Validation | `backend/scripts/check_weknora_native_model_config.py` | Runs live API plus browser workflow validation. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_model_config.py --browser
```

Sanitized output:

```text
WeKnora native model/config readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- catalog: providers=25 models=2
- parser_storage: parser_engines=9 storage_engines=7
- runtime: chat_embedding=live admin_tests=blocked_admin_only
- browser: Capability Center rendered model/config readiness
```

Additional validation:

```text
backend/.venv/bin/python -m py_compile ... -> PASS
frontend bundled node tsc --noEmit -> PASS
frontend bundled node vite build -> PASS
git diff --check -> PASS
acceptance harness static/live status -> PASS, groups=15 live=7 partial=5 blocked=0 backlog=3
sensitive scan -> reviewed benign code-field/self-test hits only
```

Evidence boundaries:

- The smoke starts temporary PA backend/frontend services and calls live PA BFF
  endpoints backed by real WeKnora native read APIs.
- The response is masked: it reports counts, statuses, model/source types,
  credential-configured booleans, and docreader configured/connected booleans.
- It does not expose raw BaseURL values, API keys, AppSecret, provider payloads,
  docreader addresses, storage credentials, `.env` values, logs, private
  endpoints, or model test responses.
- Remote model checks, embedding tests, rerank checks, parser checks, and
  storage connectivity tests remain `blocked_admin_only` because native routes
  are Admin-only and may use stored credentials or external probes.

## Coverage Impact

The `Model/embedding/rerank/parser` group remains `live-partial` with score
`0.5`. The current total coverage remains:

```text
9.75 / 15 = 65.0%
```

The final 80% target remains:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- Native model CRUD, credential mutation, remote model tests, embedding tests,
  rerank checks, parser-engine checks, and storage connectivity checks require
  an explicit operator confirmation and secret-handling design before PA should
  expose them.
- Provider catalog and model catalog visibility is not answer evidence and must
  not be counted as citation PASS.
- Deep model administration remains better owned by WeKnora native console
  unless a narrower PA operator workflow is explicitly scoped.
