# P3-M2 Intranet Runbook

This runbook is for PA AI Workbench M2 intranet pilots that use WeKnora as the
real RAG / Wiki backend. It records commands, checks, recovery steps, and
rollback rules without storing tokens, private endpoints, workspace ids, KB ids,
uploads, databases, logs, or real pilot documents.

Related docs:

- `docs/PHASE3_WEKNORA_DEPLOYMENT_MAP.md`
- `docs/PHASE3_WEKNORA_RAG_WIKI_CONFIG_CHECKLIST.md`
- `docs/PHASE3_M2_REQUEST_ID_PROPAGATION.md`
- `docs/PHASE3_M2_PILOT_FEEDBACK_TEMPLATE.md`

## Operating Rule

PA frontend and PA Agent never call WeKnora directly. The only allowed path is:

```text
PA Frontend -> PA Backend -> PA KnowledgeBackend Adapter -> WeKnora Backend
```

For pilot readiness, PA must run with:

- `KNOWLEDGE_BACKEND` set to `weknora_api`
- `MOCK_MODE` set to `false`
- `MOCK_MODEL_MODE` set to `false`
- PA chat provider configured through `ModelGateway`
- WeKnora service config supplied only by runtime environment or secret manager

## Startup Order

1. Start WeKnora infrastructure:
   - PostgreSQL / ParadeDB
   - Redis
   - selected vector store
   - object or local storage
   - DocReader
2. Start WeKnora app/API.
3. Confirm WeKnora health, auth, workspace, KB, model, vector store, Redis, and
   DocReader checks.
4. Start PA backend with WeKnora adapter env loaded from runtime secrets.
5. Start PA frontend.
6. Run PA M2 preflight and smoke checks.
7. Allow pilot users only after evidence and Wiki checks return non-mock results.

## Required Preflight Commands

Run from `pa-ai-workbench`:

```bash
backend/.venv/bin/python backend/scripts/check_m2_preflight.py
```

The command is intentionally fail-closed. `READY` requires:

- PA runtime mode is non-mock.
- WeKnora health/auth/workspace/KB checks pass.
- WeKnora has an active DeepSeek `KnowledgeQA` model.
- WeKnora has an active DashScope/Aliyun `Embedding` model.
- The selected KB has a non-empty `embedding_model_id`.
- The KB `embedding_model_id` points to an Embedding model, not a chat model.
- Embedding dimension is present and compatible with vector retrieval.
- Redis/task queue works.
- DocReader is connected.
- Vector store live test passes.
- A short sanitized retrieve probe does not report vector dimension mismatch.

Optional local sanity checks:

```bash
backend/.venv/bin/python backend/scripts/smoke_real_chat_model_m2.py
backend/.venv/bin/python backend/scripts/smoke_weknora_adapter_errors_m2.py
backend/.venv/bin/python backend/scripts/smoke_rag_debug_api_m2.py
```

For real pilot release gates, run the relevant live WeKnora smokes only in an
approved intranet environment with sanitized data.

## Model And KB Checks

### DeepSeek Chat Is Not Embedding

DeepSeek chat / `KnowledgeQA` is used for answer generation. It must not be used
as the document embedding model.

Required split:

- PA Agent chat: DeepSeek via PA `ModelGateway` with `openai_compatible`
- WeKnora KnowledgeQA: DeepSeek `KnowledgeQA`
- WeKnora Embedding: DashScope/Aliyun `Embedding`

If preflight says `KB embedding_model_id is not an Embedding model`, fix the KB
binding. Do not change PA Agent chat config as a workaround.

### KB Must Bind `embedding_model_id`

Every pilot KB used for real RAG/Wiki must bind a valid `embedding_model_id`.

Failure patterns:

- `KB has no embedding_model_id`
- `KB embedding_model_id is not in model list`
- `KB embedding_model_id is not an Embedding model`
- `KB embedding model is not DashScope/Aliyun`
- `KB embedding model dimension is missing`

Recovery:

1. Create or enable a DashScope/Aliyun Embedding model in WeKnora.
2. Confirm the model has configured credential metadata without printing it.
3. Confirm its dimension is non-zero.
4. Bind the KB `embedding_model_id` to that Embedding model.
5. Re-run `backend/.venv/bin/python backend/scripts/check_m2_preflight.py`.
6. Re-index affected sanitized pilot documents when the embedding model or
   vector dimension changed.

## Common Failures

| Symptom | Likely cause | Check | Recovery |
| --- | --- | --- | --- |
| PA returns mock citations | PA runtime still in mock mode | `check_m2_preflight.py` PA runtime config | Set non-mock runtime env and restart PA backend. |
| Upload stays processing | Redis/task queue, DocReader, or WeKnora indexing stalled | Preflight Redis and DocReader checks; document status events | Restart unhealthy service, then retry document processing from PA. |
| RAG returns no evidence | KB has no indexed chunks, wrong KB, or over-narrow filters | RAG debug trace id and adapter logs | Check document indexed state, KB binding, and query filters. |
| Vector dimension error | Embedding model dimension does not match vector store collection/table | Preflight vector dimension probe | Rebuild vector store collection/table or re-index with the correct embedding model. |
| Wiki publish succeeds but retrieval fails | Wiki page not indexed or retrieve check timed out | Wiki status and adapter `operation` logs | Wait for indexing, refresh Wiki status, or retry publish/index after fixing backend issue. |
| 401 or 403 from WeKnora | Service token, RBAC, workspace, or tenant mismatch | Adapter `error_code` and `status_code` | Rotate/fix runtime secret or service-account permission outside Git. |
| 404 from WeKnora | Wrong external document/wiki id or KB mapping | Adapter `operation`, PA document/wiki ids | Refresh mappings and retry from PA; do not invent citations. |
| 429 or 5xx from WeKnora | Rate limit or backend outage | Adapter `retry_count`, `status_code`, `error_code` | Back off, verify WeKnora health, then retry. |

## Log Troubleshooting

Use `docs/PHASE3_M2_REQUEST_ID_PROPAGATION.md` as the field reference.

From a user report:

1. Capture PA `task_id`, `document_id`, `wiki_page_id`, `output_id`, or RAG debug
   `trace_id`.
2. Search adapter logs for that id.
3. Copy the related `adapter_operation_id`.
4. Inspect `operation`, `status_code`, `retry_count`, `error_code`, and short
   redacted `excerpt`.
5. Create a pilot feedback item using
   `docs/PHASE3_M2_PILOT_FEEDBACK_TEMPLATE.md`.

Do not ask users for real documents, raw logs, screenshots with private names,
or full WeKnora responses.

## Recovery Steps

Document processing:

1. Confirm the document is not still actively processing.
2. Check document processing events for `weknora_upload`, `weknora_status`, or
   `weknora_retry`.
3. Fix the underlying WeKnora service/config issue.
4. Use the PA retry action to resubmit the stored PA document record.
5. Confirm status reaches indexed before asking Agent questions.

RAG retrieve:

1. Run RAG debug with a short sanitized query.
2. Check returned `source_type`, `source`, `score`, `evidence_id`, `chunk_id`,
   and `wiki_page_id`.
3. If no evidence appears, check KB binding, document indexed status, and filters.
4. If mock evidence appears, stop pilot acceptance and fix runtime mode.

Wiki publish:

1. Confirm source citations are traceable before publish.
2. Publish from PA; do not call WeKnora directly.
3. Refresh Wiki status until retrievable or failed.
4. If indexing times out, check adapter logs, WeKnora health, KB embedding, and
   vector store state.
5. Retry publish/index only after fixing the backend cause.

## Rollback

Use rollback when a deployment blocks pilot usage and cannot be fixed quickly.

1. Stop new pilot actions.
2. Keep existing logs and PA ids for diagnosis, but do not commit logs.
3. Re-deploy the previous known-good PA backend/frontend artifact or image.
4. Revert runtime env to the previous known-good secret set through the secret
   manager or deployment system.
5. Do not delete WeKnora data unless a designated operator confirms it is a
   disposable sanitized pilot KB.
6. Run:

```bash
backend/.venv/bin/python backend/scripts/check_m2_preflight.py
```

7. Run targeted smoke checks for the failed workflow.
8. Record the rollback in the pilot feedback template with sanitized ids.

## Git Safety Before Any Fix Commit

Run from `pa-ai-workbench`:

```bash
git status --short
git status --ignored --short
git diff --check
```

Before committing, confirm no tracked or staged file includes:

- `.env`
- uploads, data, db, logs, dist, node_modules
- API keys, tokens, authorization headers, private endpoints
- real documents or long evidence excerpts

## Operator Escalation Checklist

- [ ] Preflight command and result recorded.
- [ ] Affected PA ids recorded.
- [ ] Adapter operation id recorded.
- [ ] Category selected: bug / config / data / product feedback / out-of-scope.
- [ ] No secrets or real data included in the issue.
- [ ] Recovery or rollback owner assigned.
