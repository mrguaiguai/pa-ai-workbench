# PA AI Workbench v0.2 Demo Script

This script is for the Phase 2 v0.2 walkthrough. Use sanitized sample files only. Do not use real department materials, client names, non-public policies, credentials, API keys, or real uploads.

## Demo Goal

Show the v0.2 end-to-end loop:

1. Confirm backend, model status, embedding status, and RAG mode.
2. Demonstrate safe mock fallback.
3. Upload a sanitized document and show parse / chunk / index status.
4. Run analysis workflows with document and Wiki evidence.
5. Generate a Wiki draft from an analysis output.
6. Edit and publish a Wiki page.
7. Show Wiki citation sources and index status.
8. Verify history and git safety.

## Safety Rules

- Use only sanitized demo text files.
- Do not screen-share `.env`, API keys, private model base URLs, `backend/data/`, `backend/uploads/`, or local databases.
- Keep mock fallback available even when running real local RAG.
- If external model or embedding providers are unavailable, switch to mock mode and continue the demo.
- Treat insufficient evidence warnings as expected safeguards.
- Do not commit `.env`, uploads, databases, logs, build artifacts, or real source material.

## Demo Modes

### Mode A: Safe Mock Demo

Use this mode when no external model or embedding provider is available.

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
CHAT_MODEL_PROVIDER=mock
MOCK_MODEL_MODE=true
EMBEDDING_PROVIDER=mock
EMBEDDING_DIMENSION=1024
```

Expected behavior:

- Home page shows mock / fallback status.
- Analysis can run with mock citations.
- Wiki search and reader remain demoable.
- Evidence labels may show `Mock`.

### Mode B: Real Local RAG Demo

Use this mode only with sanitized local files and approved model credentials stored outside git.

```text
KNOWLEDGE_BACKEND=extracted
MOCK_MODE=false
DATABASE_URL=sqlite:///./data/pa_workbench.db
UPLOAD_DIR=./uploads
CHAT_MODEL_PROVIDER=openai-compatible
CHAT_MODEL_BASE_URL=<configured-outside-git>
CHAT_MODEL_API_KEY=<configured-outside-git>
CHAT_MODEL_NAME=<chat-model-name>
MOCK_MODEL_MODE=false
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=<configured-outside-git>
EMBEDDING_API_KEY=<configured-outside-git>
EMBEDDING_MODEL_NAME=<embedding-model-name>
EMBEDDING_DIMENSION=<embedding-dimension>
```

Expected behavior:

- `/api/model/status` shows chat and embedding providers configured.
- Library documents progress through parse / chunk / index states.
- Analysis citations can include `Document` and `Wiki`.
- Wiki pages can be drafted, edited, published, and later retrieved as evidence.

## Setup Checklist

Start the backend:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Pre-demo checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/model/status
```

Expected:

- `/health` returns `status=ok`.
- `/api/status` returns `knowledge_backend`, `mock_mode`, and counts.
- `/api/model/status` returns chat and embedding provider status without exposing API keys.
- Home page displays backend, model, embedding, and RAG status cards.
- `git status --short` does not show `.env`, databases, uploads, or real documents staged.

## Demo Data

Create a tiny sanitized demo file outside tracked source control or in a temporary ignored location:

```text
Title: Sanitized Public Affairs Policy Note

The public affairs team should track policy changes, record evidence for claims,
prepare stakeholder briefing notes, and maintain a reusable Wiki of approved
insights. This synthetic file is for local demo only.
```

Suggested metadata:

```text
Title: Sanitized Public Affairs Policy Note
Business area: public_affairs
Document type: policy_note
Source: sanitized_demo
Keywords: policy, briefing, evidence, wiki
```

## Walkthrough

### 1. Home: Runtime Status

Open `/`.

Say:

> The v0.2 home page shows whether the backend, model gateway, embedding provider, and RAG pipeline are configured. The status cards expose provider names and booleans only, never API keys.

Show:

- Backend status badge.
- Chat Model status.
- Embedding status.
- RAG Pipeline status.
- Core metrics including documents, chunks, tasks, and outputs.

Success cue:

- Status cards are ready, or clearly show mock fallback / missing configuration.

### 2. Library: Parse, Chunk, Index

Open `/library`.

Say:

> The library is where sanitized materials enter the RAG loop. v0.2 shows parse status, chunk counts, embedding / indexed status, chunk previews, and reindex controls.

Show:

- Upload form.
- Document status badges.
- Chunk count and indexed count.
- Chunk preview.
- Reindex button.

Action:

1. Upload the sanitized demo file.
2. Wait for parse / chunk / index status.
3. Open chunk preview.

Success cue:

- The document appears with chunk count and indexed status, or a clear failure reason.

Fallback:

- If indexing fails because model credentials are unavailable, switch to Mode A mock demo and explain mock fallback.

### 3. Analysis: Knowledge QA With Evidence

Open `/analysis` and choose `知识问答`.

Prompt:

```text
请基于资料库说明公共事务团队为什么需要维护可追溯的证据和 Wiki，并列出依据。
```

Say:

> Analysis uses the Agent runtime, Model Gateway, retrieval tools, and citation checker. The result should show whether it used real RAG, mock fallback, document evidence, Wiki evidence, or insufficient evidence warnings.

Show:

- Workflow selector.
- Result panel.
- RAG mode summary.
- Evidence source counts.
- Citation list with `Document`, `Wiki`, or `Mock` labels.
- Insufficient evidence warning if present.

Success cue:

- The answer includes citations or an explicit insufficient evidence warning.

### 4. Analysis: Policy And Case Workflows

Run `政策分析`.

Prompt:

```text
分析这份 sanitized policy note 对公共事务团队的影响，输出背景、核心要求、风险和建议。
```

Run `案例复盘`.

Prompt:

```text
基于 sanitized demo 材料复盘一次公共事务知识沉淀案例，说明背景、动作、结果和经验。
```

Show:

- Policy output sections.
- Case review output sections.
- Citations and warnings.

Success cue:

- Outputs are structured and traceable to evidence or warnings.

### 5. Generate Wiki Draft From Analysis

After a successful analysis output, click `生成 Wiki 草稿`.

Say:

> v0.2 can convert an analysis output into a Wiki draft while preserving source output and citation references.

Show:

- Draft creation state.
- Draft title and slug.
- `查看草稿` opens the Wiki page.

Success cue:

- A draft Wiki page opens with status `draft`.

Fallback:

- If draft creation fails, keep the analysis result and show the API error state. Do not fabricate a Wiki page.

### 6. Wiki: Edit And Publish

Open `/wiki`.

Action:

1. Select the generated draft.
2. Click edit.
3. Adjust title, summary, tags, or markdown using sanitized text.
4. Save draft.
5. Publish.

Say:

> Wiki pages have draft and published states. Publishing is explicit so the team can review generated content before it becomes reusable knowledge.

Show:

- Editor fields.
- Save draft action.
- Publish action.
- Published status.

Success cue:

- Page status changes to `published` and `published_at` is populated.

### 7. Wiki: Citation Sources And Index Status

Still in `/wiki`, show the right side panel.

Say:

> The Wiki page keeps source references and citation bindings. The index panel shows whether the page has been embedded and indexed for retrieval.

Show:

- Index status.
- Published / indexed timestamps.
- Source output id.
- Source document ids.
- Source citation ids.
- Wiki citation bindings.
- Evidence list.

Success cue:

- Source refs and citation bindings are visible, or the UI clearly shows that none are available.

### 8. Retrieve Wiki Evidence

Return to `/analysis` and ask a question that should match the published Wiki page.

Prompt:

```text
根据已发布 Wiki，总结公共事务团队如何把分析结论沉淀为可复用知识。
```

Show:

- Evidence source count includes Wiki when indexed and retrievable.
- Citation list labels Wiki evidence.
- If Wiki evidence is absent, show index status and explain reindex / embedding prerequisites.

Success cue:

- The answer uses Wiki evidence, document evidence, or a transparent insufficient evidence warning.

### 9. History

Open `/history`.

Say:

> Generated outputs remain auditable after the conversation moves on. History keeps output status, warnings, citations, and result content visible.

Show:

- Outputs from QA / policy / case workflows.
- Warnings.
- Citations.
- Evidence source labels.

Success cue:

- Recent outputs appear and remain inspectable.

## API Smoke Commands

Use these only with sanitized data:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/model/status
```

Optional retrieval debug:

```bash
curl -X POST http://127.0.0.1:8000/api/rag/retrieve \
  -H 'Content-Type: application/json' \
  -d '{"query":"public affairs evidence wiki","top_k":5,"filters":{}}'
```

Expected:

- Retrieval returns evidence items, or an empty result with no sensitive leakage.
- Evidence items identify source type such as document chunk or Wiki page.

## Failure And Fallback Paths

- Backend unavailable: restart `uvicorn`, then refresh the frontend.
- Frontend unavailable: restart Vite and confirm `VITE_API_BASE_URL` points to `http://127.0.0.1:8000` if customized.
- Model status missing config: switch chat and embedding providers to mock mode.
- Embedding dimension mismatch: reindex documents and Wiki pages after fixing `EMBEDDING_DIMENSION`.
- No citations: present insufficient evidence as a safeguard.
- Wiki not retrieved: confirm the page is published and indexed, then rerun retrieval.
- Upload or parse fails: use a smaller sanitized `.txt` or `.md` file.

## Closing Message

Say:

> v0.2 demonstrates the real knowledge loop: sanitized materials enter the library, the system parses and indexes them, Agent workflows produce evidence-bound outputs, analysis results can become reviewed Wiki pages, and published Wiki knowledge can feed future retrieval. Mock fallback keeps the product demoable without external services, while status panels make configuration visible without exposing secrets.

## Post-Demo Safety Checks

Run:

```bash
git status --short
git status --ignored --short
```

Confirm:

- No `.env` files are staged.
- No uploads, SQLite databases, logs, real documents, or API keys are staged.
- `backend/data/`, `backend/uploads/`, `frontend/dist/`, `frontend/node_modules/`, `.venv/`, and `__pycache__/` remain ignored.
- Any temporary sanitized demo file is deleted or left outside tracked source.
