# PA AI Workbench

PA AI Workbench is an independent internal productivity product for a financial public affairs team.

The v0.2 version focuses on:

- Local knowledge base and document upload
- Real document parse / chunk / embedding / retrieve workflow with mock fallback
- RAG question answering with document and Wiki citations
- Policy analysis and case review workflows through the Model Gateway
- Historical case retrieval
- Wiki draft / edit / publish / retrieve workflow
- Modular Agent runtime with persistent conversation memory

In the combined PA + WeKnora worktree, this product remains independently structured under `pa-ai-workbench/` while using WeKnora native APIs as its capability source through the PA backend BFF.

## Local Startup

Use mock mode for the safest local demo. Do not copy real credentials, real department documents, uploads, or SQLite databases into git.

### 1. Backend

Create a local environment if needed:

```bash
cd pa-ai-workbench/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Safe default configuration:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
CHAT_MODEL_PROVIDER=mock
MOCK_MODEL_MODE=true
EMBEDDING_PROVIDER=mock
```

Start the API:

```bash
cd pa-ai-workbench/backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Smoke check:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/model/status
```

### 2. Frontend

Install dependencies and start Vite:

```bash
cd pa-ai-workbench/frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Build check:

```bash
cd pa-ai-workbench/frontend
npm run build
```

If `npm` is not on PATH, install Node.js 18+ or set `NODE_BIN` before using
`scripts/pa-dev-services.sh`.

## v0.2 Model And RAG Configuration

All model calls should go through the backend Model Gateway. All embedding calls should go through the configured Embedding Provider. Keep mock fallback available for demos and offline development.

### Mock Mode

Use mock mode when you need a safe local demo without external model calls:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
CHAT_MODEL_PROVIDER=mock
MOCK_MODEL_MODE=true
EMBEDDING_PROVIDER=mock
EMBEDDING_DIMENSION=1024
```

### Real Local RAG

Use the extracted backend when you want to parse, chunk, embed, index, and retrieve real local documents:

```text
KNOWLEDGE_BACKEND=extracted
MOCK_MODE=false
DATABASE_URL=sqlite:///./data/pa_workbench.db
UPLOAD_DIR=./uploads
```

This stores local SQLite data under `backend/data/` and uploads under `backend/uploads/`. Both are ignored and must not be committed.

### OpenAI-Compatible Chat Model

Configure only in `backend/.env` or your shell environment:

```text
CHAT_MODEL_PROVIDER=openai-compatible
CHAT_MODEL_BASE_URL=https://example-model-endpoint/v1
CHAT_MODEL_API_KEY=
CHAT_MODEL_NAME=<chat-model-name>
CHAT_MODEL_TIMEOUT_SECONDS=60
CHAT_MODEL_TEMPERATURE=0.2
MOCK_MODEL_MODE=false
```

Fill API key values locally. Do not commit real provider keys or private
endpoints.

### OpenAI-Compatible Embeddings

Configure embeddings separately from chat:

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://example-embedding-endpoint/v1
EMBEDDING_API_KEY=
EMBEDDING_MODEL_NAME=<embedding-model-name>
EMBEDDING_DIMENSION=1024
EMBEDDING_TIMEOUT_SECONDS=60
```

`EMBEDDING_DIMENSION` must match the embedding model. Reindex documents or Wiki pages after changing embedding model or dimension.

### Runtime Status

The home page shows backend, model, embedding, and RAG status using:

```text
GET /api/status
GET /api/model/status
```

These endpoints expose provider names and configuration booleans only. They do not expose API keys.

## Main Routes

- `/` - workbench overview, backend status, model status, embedding status, and RAG mode.
- `/library` - document upload, parse/index status, chunk preview, and reindex controls.
- `/analysis` - knowledge QA, policy analysis, case review, evidence display, and Wiki draft creation.
- `/wiki` - Wiki search, reader, draft creation, edit, publish, citation sources, and index status.
- `/history` - generated output history with warnings and citations.

## v0.2 Workflow

Typical local RAG loop:

1. Start backend and frontend.
2. Open `/library`, upload a sanitized local document, and let it parse / chunk / index.
3. Open `/analysis`, run knowledge QA / policy analysis / case review.
4. Inspect document / Wiki evidence and insufficient-evidence warnings.
5. Generate a Wiki draft from an analysis result.
6. Open `/wiki`, edit the draft, publish it, and inspect citation sources / index status.
7. Re-run analysis to allow published Wiki evidence to participate in retrieval.

For the older MVP walkthrough, see `docs/DEMO_SCRIPT.md` if present. The phase-2 demo script is tracked separately in `PHASE2_SPEC.md` as a later task.

## Development Entry

Read these files before implementation:

- `DEV_SPEC.md`
- `PHASE2_SPEC.md`
- `PRODUCT_SPEC.md`
- `.github/skills/auto-coder/SKILL.md`
- `.github/skills/qa-tester/SKILL.md`
- `.github/skills/setup/SKILL.md`
- `.github/skills/phase2-rag-auditor/SKILL.md`
- `.github/skills/phase2-auto-coder/SKILL.md`
- `.github/skills/phase2-qa-tester/SKILL.md`

Suggested development prompt:

```text
Please read pa-ai-workbench/DEV_SPEC.md and use the auto-coder skill to execute the next unchecked task. After finishing, update DEV_SPEC.md and report changed files, validation result, and next task.
```

Phase 2 development prompt:

```text
Please read pa-ai-workbench/PHASE2_SPEC.md and use the phase2-auto-coder skill to execute the next unchecked task. After finishing, update PHASE2_SPEC.md and report changed files, validation result, and next task.
```

## Git Safety

Do not commit:

- Real department documents
- Uploaded files
- SQLite databases
- `.env` files
- API keys or credentials
- Local cache/build artifacts
- Model provider base URLs if they are private
- Any prompt/output containing sensitive source material

Before committing, run:

```bash
git status --short
git status --ignored --short
```

Expected ignored local artifacts include `backend/.venv/`, `backend/data/`, `backend/uploads/`, `frontend/node_modules/`, `frontend/dist/`, and Python `__pycache__/` directories.
