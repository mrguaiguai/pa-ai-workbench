# Phase 5 Real Test Runbook

This runbook explains how to repeat the Phase 5 local real test flow for PA AI
Workbench. It keeps PA as the product boundary: tests must go through PA backend
APIs, PA Adapter, or PA workflow scripts. Do not call raw WeKnora or model
providers directly for final PASS evidence.

## Scope

Use this from the repo root:

```bash
cd /path/to/pa-ai-workbench
```

The test corpus is the synthetic sanitized Phase 4 corpus:

```text
backend/fixtures/phase4_rag_wiki_qa/
```

The final real PASS path requires:

```text
MOCK_MODE=false
KNOWLEDGE_BACKEND=weknora_api
source=weknora_api
fresh/current-run evidence scope
```

Do not record tokens, private endpoints, uploaded file bodies, raw chunks,
database contents, logs, prompts, or provider outputs in reports.

## Environment

Configure the backend environment locally before starting services. Keep the
actual values outside reports and commits.

Required categories:

```text
WEKNORA_BASE_URL
WEKNORA_SERVICE_TOKEN
WEKNORA_DEFAULT_KB_ID
WEKNORA_WORKSPACE_ID
KNOWLEDGE_BACKEND=weknora_api
MOCK_MODE=false
CHAT_MODEL_PROVIDER
CHAT_MODEL_BASE_URL
CHAT_MODEL_API_KEY
CHAT_MODEL_NAME
MOCK_MODEL_MODE=false
```

Optional Phase 5 timing knobs:

```text
PHASE5_B5_WAIT_SECONDS
PHASE5_B5_POLL_SECONDS
PHASE5_B5_TOP_K
PHASE5_F1_TOP_K
PHASE5_F1_TIMEOUT_SECONDS
PHASE5_F2_TIMEOUT_SECONDS
```

## Backend 后端

Start the backend from the nested repo:

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, check the backend status:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/status
```

The status evidence should show `KNOWLEDGE_BACKEND=weknora_api`,
`MOCK_MODE=false`, and a connected WeKnora health state before final PASS work.

## Frontend 前端

Start the frontend from the nested repo:

```bash
cd frontend
npm run dev
```

Open the Vite URL shown by the command. In this checkout the usual local URL is:

```text
http://127.0.0.1:5173
```

If the page loads but API calls show `failed to fetch`, check that the backend
is running on `127.0.0.1:8000` before debugging React.

Build validation:

```bash
cd frontend
npm run build
```

## Fixture Upload And Wiki Publish

Final PASS must use a fresh/current-run scope, not old cached uploads. The
existing all-in-one real scripts can prepare the Phase 4 documents and published
Wiki page as part of their own run:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/run_phase5_b5_real_rag_matrix.py
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/run_phase5_d5_real_knowledge_qa.py
```

For P5-G, prefer an explicit upload/index step that records a current-run handoff
file for reusable RAG and knowledge_qa scripts. The handoff JSON should contain
only sanitized identifiers:

```json
{
  "current_run": {
    "run_id": "phase5-current-run-id",
    "corpus_id": "phase4_rag_wiki_qa_v1",
    "namespace": "phase5-current-run-id",
    "external_doc_ids": ["fresh-document-id"],
    "knowledge_ids": ["fresh-knowledge-id"],
    "wiki_page_ids": ["fresh-wiki-page-id", "phase5/wiki-slug"],
    "anchors": [
      "TEST-RAG-001",
      "TEST-RAG-002",
      "TEST-RAG-003",
      "TEST-RAG-004",
      "TEST-RAG-005",
      "TEST-RAG-006",
      "TEST-RAG-007",
      "TEST-WIKI-001",
      "TEST-DISTRACTOR-001"
    ]
  },
  "knowledge_base_ids": ["configured-kb-id"]
}
```

Do not put endpoint URLs, tokens, upload paths, raw chunks, database rows, logs,
or provider output in that handoff file.

## RAG 24 问

For a repeatable RAG 24-question check through PA backend `/api/rag/retrieve`:

```bash
python3 backend/scripts/run_phase5_f1_real_rag_matrix.py --mode dry
```

Real mode requires the backend and a fresh/current-run handoff:

```bash
python3 backend/scripts/run_phase5_f1_real_rag_matrix.py \
  --mode real \
  --api-base-url http://127.0.0.1:8000 \
  --current-run-json /path/to/current_run.json \
  --output docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md
```

Acceptance checks:

```bash
test -f docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md
rg -n "P4Q-001|P4Q-024|PASS|source_type|trace_id|TEST-DISTRACTOR-001|PHASE5_REAL" docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md
```

The script must return nonzero for any non-PASS result.

## Wiki

Wiki publish/index/retrieve/citation evidence can be checked with the real Wiki
closed-loop script:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/run_phase5_c4_real_wiki_pass.py
```

Acceptance checks:

```bash
test -f docs/PHASE5_REAL_WIKI_PASS_REPORT.md
rg -n "P4Q-017|P4Q-019|source_type=wiki_page|wiki_page_id|PASS|PHASE5_REAL" docs/PHASE5_REAL_WIKI_PASS_REPORT.md
```

The report must prove draft creation, publish, read back, indexed/retrievable
state, Wiki-only retrieval, and citation location.

## knowledge_qa 24 问

For a repeatable `knowledge_qa` 24-question check through PA `/api/analysis/run`:

```bash
python3 backend/scripts/run_phase5_f2_real_knowledge_qa_matrix.py --mode dry
```

Real mode requires the backend and a fresh/current-run handoff:

```bash
python3 backend/scripts/run_phase5_f2_real_knowledge_qa_matrix.py \
  --mode real \
  --api-base-url http://127.0.0.1:8000 \
  --current-run-json /path/to/current_run.json \
  --output docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md
```

Acceptance checks:

```bash
test -f docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md
rg -n "P4Q-001|P4Q-024|knowledge_qa|PASS|依据不足|TEST-DISTRACTOR-001|新版|PHASE5_REAL" docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md
```

The script must check answer points, citation source types, insufficient
evidence refusal, distractor suppression, and version-conflict handling.

## Frontend Browser Acceptance

Frontend acceptance should cover these pages in a real browser session:

```text
首页
资料库
RAG 调试
Wiki
知识问答
历史
```

Required report:

```bash
test -f docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md
rg -n "首页|资料库|RAG 调试|Wiki|知识问答|历史|PASS|PHASE5_REAL" docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md
```

The browser report should record visible text and status evidence. Screenshots
may stay in a temporary local directory and should not be committed.

## Report Check

Run the Phase 5 report safety checker before marking final tasks complete:

```bash
python3 backend/scripts/check_phase5_report_safety.py --self-test
python3 backend/scripts/check_phase5_report_safety.py
```

The checker scans `docs/PHASE5_REAL_*.md` for sensitive data risks and required
evidence fields such as `source`, `source_type`, `evidence_id`, `chunk_id`,
`wiki_page_id`, and `trace_id`.

## Final Gate Order

Recommended P5-G order:

```text
P5-G1 environment preflight report
P5-G2 fresh/current-run upload and index report
P5-G3 RAG 24-question PASS report
P5-G4 Wiki closed-loop PASS report
P5-G5 knowledge_qa 24-question PASS report
P5-G6 frontend browser PASS report
P5-G7 final Phase 5 PASS report
```

Each P5-G task must have its own report and must not be marked complete for
PARTIAL, FAIL, BLOCKED, mock-only, fixture-only, old-cache, or fallback evidence.

## 禁止提交

Do not commit these files or directories:

```text
.env
backend/.env
frontend/.env
backend/uploads/
backend/data/
backend/logs/
frontend/dist/
node_modules/
__pycache__/
*.log
*.sqlite
*.sqlite3
*.db
```

Do not commit reports containing:

```text
API keys
authorization headers
service tokens
private endpoints
private addresses
raw uploaded file bodies
raw chunks
database dumps
logs
unredacted prompts
provider outputs
real company, person, customer, project, or policy identifiers
```

Use only sanitized Phase 4 anchors such as `TEST-RAG-001`,
`TEST-WIKI-001`, and `TEST-DISTRACTOR-001` for acceptance evidence.
