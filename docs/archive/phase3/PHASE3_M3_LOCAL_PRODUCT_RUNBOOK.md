# Phase 3 M3 Local Product Runbook

This runbook is the M3 handoff path for running PA AI Workbench as a local
product with live WeKnora RAG/Wiki capability and public model APIs. It is not
a mock demo path. Keep tokens, endpoints, uploads, databases, logs, and real
materials outside Git.

## Product Boundary

The only allowed runtime path is:

```text
PA Frontend -> PA Backend -> PA KnowledgeBackend Adapter -> WeKnora Backend
```

PA frontend and PA Agent must not call WeKnora directly. Agent outputs must use
PA `Evidence` and `Citation` shapes, and citations must trace to a WeKnora
document chunk or Wiki page before they count as real evidence.

## Required Runtime Mode

For M3 local product acceptance:

- `APP_ENV` is `local`, `pilot`, `staging`, or `intranet`.
- `KNOWLEDGE_BACKEND` is `weknora_api`.
- `MOCK_MODE` is `false`.
- `MOCK_MODEL_MODE` is `false`.
- PA Chat uses DeepSeek through `ModelGateway`.
- WeKnora `KnowledgeQA` uses DeepSeek.
- WeKnora Embedding uses DashScope/Aliyun Embedding.
- The selected KB has a valid `embedding_model_id` bound to an Embedding model.

`extracted` is allowed only as an explicit dev/local fallback. It must show
local/sync-pending state and must never label fallback evidence as
`source=weknora_api`.

## Empty Data Startup

Start from a disposable local product dataset or an approved sanitized pilot KB.
Do not commit generated data.

1. Start WeKnora infrastructure: database, Redis, vector store, object/local
   storage, and DocReader.
2. Start WeKnora app/API and confirm health.
3. Configure WeKnora workspace, KB, DeepSeek `KnowledgeQA`, DashScope/Aliyun
   `Embedding`, vector store binding, Redis, and DocReader.
4. Start PA backend with runtime environment supplied by shell or secret
   manager.
5. Start PA frontend.
6. Run M3 local product checker.
7. Allow users only after live gates prove non-mock WeKnora evidence.

Suggested PA commands from `pa-ai-workbench`:

```bash
backend/.venv/bin/python backend/scripts/check_m3_local_product.py
backend/.venv/bin/python backend/scripts/check_m3_local_product.py --run-live-smokes
```

The first command is the static/fixture contract gate. The second command is
the live local product gate and may upload sanitized fixtures or call public
model APIs through existing live smoke scripts.

## Backend And Frontend Startup

Backend:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Open the local UI at the Vite dev server shown by `npm run dev`. If a port is
already in use, choose the next available local port and keep `VITE_API_BASE_URL`
pointing to the PA backend.

## Readiness Surfaces

Before uploading material, confirm the home page/status surface shows:

- Chat Model configured, mock disabled, provider/model visible, API key only as
  configured/not configured.
- Embedding configured, mock disabled, provider/model/dimension visible, API key
  only as configured/not configured.
- RAG Pipeline active backend is `weknora_api`, mock disabled, WeKnora connected.
- Capability readiness shows supported/partial/unsupported counts, fail-closed
  status, citation trace status, Wiki publish status, and debug status.

Backend endpoints used by the UI:

```text
GET /api/status
GET /api/model/status
GET /api/capabilities
```

These responses must not expose tokens, raw endpoints, passwords, private KB
ids, or long source excerpts.

## Required Checks

Run static/fixture gates:

```bash
backend/.venv/bin/python backend/scripts/smoke_backend_capability_matrix_m3.py
backend/.venv/bin/python backend/scripts/smoke_backend_feature_flags_m3.py
backend/.venv/bin/python backend/scripts/check_m3_backend_switch.py
backend/.venv/bin/python backend/scripts/smoke_knowledge_backend_contract_m3.py
backend/.venv/bin/python backend/scripts/smoke_retrieval_parameters_m3.py
backend/.venv/bin/python backend/scripts/smoke_retrieval_quality_golden_m3.py
backend/.venv/bin/python backend/scripts/smoke_rag_quality_evaluation_m3.py
backend/.venv/bin/python backend/scripts/smoke_agent_faithfulness_m3.py
backend/.venv/bin/python backend/scripts/smoke_wiki_fallback_sync_m3.py
```

Run live gates only in an approved local product environment:

```bash
backend/.venv/bin/python backend/scripts/check_m2_preflight.py
backend/.venv/bin/python backend/scripts/smoke_real_chat_model_m2.py
backend/.venv/bin/python backend/scripts/smoke_weknora_rag_m1.py
backend/.venv/bin/python backend/scripts/smoke_weknora_wiki_m1.py
backend/.venv/bin/python backend/scripts/smoke_weknora_agent_real_llm_m2.py
backend/.venv/bin/python backend/scripts/smoke_wiki_real_llm_m2.py
```

Live gates must use sanitized materials. They may call public model APIs and
may create temporary WeKnora documents or Wiki pages.

## End-To-End Acceptance

Use one sanitized Markdown/PDF/DOCX document that contains no real personal,
department, customer, incident, financial, or credential material.

1. Open the home page and record readiness as non-mock.
2. Open Library and upload the sanitized document.
3. Wait until the document reaches indexed state.
4. Inspect chunk/evidence preview and confirm `source=weknora_api`.
5. Run knowledge QA and confirm every key fact has a numbered citation.
6. Run policy analysis and confirm it cites document or Wiki evidence.
7. Run case review and confirm it does not invent case details.
8. Create a Wiki draft from an Agent result.
9. Publish the Wiki page through PA.
10. Confirm Wiki status becomes retrievable or reports a clear blocked/degraded
    state.
11. Run retrieve/debug or analysis again and confirm a `wiki_page` evidence hit.
12. Open History and confirm output warnings, citations, WeKnora citation count,
    source type, evidence id, chunk id or wiki page id, and source locator are
    visible.
13. Confirm no mock citation is counted as live acceptance evidence.

## Fallback Rules

Release-like local product mode is fail-closed:

- Missing WeKnora config plus `MOCK_MODE=false` blocks startup or readiness.
- `APP_ENV=pilot`, `staging`, or `intranet` must not silently fallback to mock.
- `mock` is dev-only and cannot count as release evidence.
- `extracted` is explicit-only and local/sync-pending; it cannot claim WeKnora
  retrievability.
- If public model APIs are unavailable, show blocked/degraded status and retry
  after recovery. Do not switch to mock to pass live acceptance.
- If retrieval returns no usable evidence, Agent output must include a clear
  `NO_EVIDENCE`/`依据不足` warning and must not produce unsupported factual
  conclusions.

## Troubleshooting

| Symptom | Likely cause | First check | Recovery |
| --- | --- | --- | --- |
| Home shows mock fallback | Runtime mode still mock or WeKnora config missing | `/api/status` and `/api/capabilities` | Fix runtime env and restart PA backend. |
| Preflight says KB embedding is wrong | KB `embedding_model_id` points to chat or missing model | `check_m2_preflight.py` | Bind DashScope/Aliyun Embedding and re-index sanitized docs. |
| Upload never indexes | Redis, DocReader, vector store, or WeKnora task issue | document processing events and preflight | Fix service, retry upload/index from PA. |
| QA has no evidence | Empty KB, wrong KB, filters too narrow, or indexing incomplete | RAG debug trace | Fix KB/index/filter before judging Agent quality. |
| Wiki publishes but retrieve misses it | Wiki index lag or backend indexing failure | Wiki status and retrieve debug | Wait, refresh status, or retry publish/index after fixing backend. |
| Unsupported claims appear | Prompt/model regression | `smoke_agent_faithfulness_m3.py` | Adjust Agent prompt/policy and rerun C4. |

## Rollback

1. Stop new live product actions.
2. Preserve PA ids and sanitized operation ids for diagnosis.
3. Re-deploy the previous known-good PA backend/frontend artifacts.
4. Restore previous runtime secret set through the secret manager or shell.
5. Do not delete WeKnora data unless the KB is confirmed disposable and
   sanitized.
6. Rerun `backend/.venv/bin/python backend/scripts/check_m3_local_product.py`.
7. Rerun `backend/.venv/bin/python backend/scripts/check_m3_local_product.py --run-live-smokes`.

## Git Safety

Before any follow-up commit:

```bash
git status --short
git status --ignored --short
git diff --check
```

Do not commit `.env`, API keys, uploads, `data`, `logs`, `db`, `dist`,
`node_modules`, local databases, real materials, screenshots with private data,
or long source excerpts.
