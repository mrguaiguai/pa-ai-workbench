# PA AI Workbench

PA AI Workbench is an independent internal productivity product for a financial public affairs team.

The first version focuses on:

- Local knowledge base and document upload
- RAG question answering
- Policy analysis workflow
- Historical case retrieval
- Wiki knowledge accumulation
- Modular Agent runtime with persistent conversation memory

This repository is intentionally separated from the upstream WeKnora source tree. WeKnora can be used as a reference or RAG capability source, but this product should remain independently structured under `pa-ai-workbench/`.

## Local Startup

Use the mock Knowledge Engine for the default MVP demo. Do not copy real credentials into this repo.

### 1. Backend

Create a local environment if needed:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Keep these defaults for a safe local demo:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
```

Start the API:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Smoke check:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
```

### 2. Frontend

Install dependencies and start Vite:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Build check:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/frontend
npm run build
```

## Main Routes

- `/` - workbench overview and backend status.
- `/library` - document upload, document list, and indexing status.
- `/analysis` - knowledge QA, policy analysis, and case review workflows.
- `/wiki` - Wiki search and page reader.
- `/history` - generated output history with warnings and citations.

## Demo Script

Use `docs/DEMO_SCRIPT.md` for the MVP walkthrough. It includes setup checks, safe mock prompts, fallback paths, and post-demo git safety checks.

## Development Entry

Read these files before implementation:

- `DEV_SPEC.md`
- `PRODUCT_SPEC.md`
- `.github/skills/auto-coder/SKILL.md`
- `.github/skills/qa-tester/SKILL.md`
- `.github/skills/setup/SKILL.md`

Suggested development prompt:

```text
Please read pa-ai-workbench/DEV_SPEC.md and use the auto-coder skill to execute the next unchecked task. After finishing, update DEV_SPEC.md and report changed files, validation result, and next task.
```

## Git Safety

Do not commit:

- Real department documents
- Uploaded files
- SQLite databases
- `.env` files
- API keys or credentials
- Local cache/build artifacts

Before committing, run:

```bash
git status --short
git status --ignored --short
```

Expected ignored local artifacts include `backend/.venv/`, `backend/data/`, `backend/uploads/`, `frontend/node_modules/`, and `frontend/dist/`.
