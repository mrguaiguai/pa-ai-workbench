# Phase 4 Real Environment Precheck Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G1 real environment and configuration precheck |
| Test time | 2026-06-15 16:21:44 CST |
| Test environment | Local PA AI Workbench workspace; backend checks from CLI; frontend production build check |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL configured; service token configured; workspace configured; default KB configured; token and endpoint intentionally omitted |
| Test scope | Configuration, read-only WeKnora connectivity, PA backend import/compile, frontend build, Phase 4 fixture safety precheck |
| Test result / 测试结果 | PARTIAL / 部分通过 |

## Precheck Results

| Check | Result | Evidence Summary | Risk / Diagnosis |
| --- | --- | --- | --- |
| Config mode | PASS | `KNOWLEDGE_BACKEND=weknora_api`; `MOCK_MODE=false`; WeKnora config fields are present and non-fixture | None for mode selection |
| Model mode | PASS | `CHAT_MODEL_PROVIDER=openai_compatible`; `MOCK_MODEL_MODE=false` | Real model config is enabled, but P4-G1 did not call the model |
| WeKnora read-only connection smoke | PASS | `smoke_weknora_connection.py` passed in live mode for health, auth, workspace, and knowledge base checks | Endpoint and identity details are omitted from this report |
| PA runtime WeKnora status service | PARTIAL | `get_weknora_status()` returned `mode=weknora_api`, `configured=true`, but `status=unavailable` and `connected=false` | Runtime status health interpretation conflicts with the live connection smoke and may mislead the frontend |
| Backend code readiness | PASS | `backend/.venv/bin/python -m compileall backend/app agent knowledge_engine` completed successfully | Compile check only; no upload or RAG query was executed |
| Frontend build | PASS | TypeScript no-emit passed; Vite production build passed using project `node_modules` and bundled Node | Shell `npm` is not on PATH; use project-local tooling or restore npm for routine checks |
| Fixture manifest and question set | PASS | `phase4_rag_wiki_qa_v1`; 9 documents; 24 questions; 0 missing fixture documents | Fixture-only validity is not real live acceptance |
| Fixture safety keyword scan | PASS with note | Keyword hits were safety disclaimers, no-answer prompts, and forbidden-content policy text inside synthetic fixtures | Keep reviewing future fixture changes so real names, tokens, uploads, databases, and logs are not committed |

## Real Capability Evidence

P4-G1 did not upload documents, publish Wiki pages, run RAG debug queries, or execute `knowledge_qa`.

| Field | Value |
| --- | --- |
| `source` | Not produced in P4-G1 |
| `source_type` | Not produced in P4-G1 |
| `evidence_id` | Not produced in P4-G1 |
| `chunk_id` | Not produced in P4-G1 |
| `wiki_page_id` | Not produced in P4-G1 |
| `trace_id` | Not produced in P4-G1 |

## Blockers / 阻塞

No hard blocker was found for starting P4-G2, because the read-only WeKnora connection smoke passed in live mode and required real-mode config is present.

However, P4-G1 cannot be marked as a clean PASS because the PA runtime status service reports WeKnora as unavailable while the connection smoke reports live connectivity. This is a status-consistency blocker for frontend trust and operational diagnosis, even if upload/index testing can proceed.

## Improvement Recommendations / 改进建议

### RAG

- In P4-G2 and P4-G3, record current-run document identifiers and evidence identifiers so old uploaded chunks or cached results cannot be mistaken for current live evidence.
- Add a lightweight real-mode preflight before RAG matrix runs that confirms `source=weknora_api` on a current retrieve, not just a successful auth check.

### Wiki

- Before P4-G4, verify that Wiki status checks use the same health/connectivity interpretation as the read-only connection smoke.
- Report draft, published, indexed, and retrievable as separate states so a frontend status mismatch cannot hide a Wiki indexing issue.

### QA

- Keep `knowledge_qa` real-test reporting separate from model prose quality until P4-G5; P4-G1 only confirms the environment can support later QA testing.
- For no-answer questions, require an explicit insufficient-evidence outcome even if retrieval returns similar live material.

### Frontend

- Fix or explain the mismatch where PA runtime status returns WeKnora unavailable while the live connection smoke passes, because users may otherwise see a false unavailable state.
- Restore a normal `npm` command on PATH or document the bundled Node/project-local build command for repeatable frontend checks.

### Config / Ops

- Do not print or commit service tokens, real endpoints, uploaded files, databases, logs, or unredacted model outputs in any P4-G report.
- Align the runtime status health check with `smoke_weknora_connection.py` or document why they intentionally use different readiness criteria.
- Keep P4-G2 gated on `MOCK_MODE=false`, `KNOWLEDGE_BACKEND=weknora_api`, non-fixture WeKnora config, and current-run upload evidence.
