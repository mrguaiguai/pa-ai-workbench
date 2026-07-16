---
name: setup
description: Setup skill for PA AI Workbench. Use when the user says "setup", "初始化", "启动项目", "环境配置", "run project", "first run", or wants to install dependencies and launch backend/frontend.
---

# Setup

This skill configures and launches PA AI Workbench locally.

## Pipeline

```text
Preflight
-> Prepare env
-> Install backend deps
-> Install frontend deps
-> Start backend
-> Start frontend
-> Smoke test
-> Report URLs
```

## Step 1: Preflight

Check current directory contains:

```text
docs/archive/legacy-product/DEV_SPEC.md
```

Check Python:

```bash
python --version
```

Recommended:

```text
Python >= 3.10
```

Check Node:

```bash
node --version
npm --version
```

Recommended:

```text
Node >= 18
```

## Step 2: Prepare Backend Env

Go to:

```bash
cd apps/pa-api
```

If `.env` does not exist, create it from `.env.example`.

Default MVP config for development-only quickstart:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
DATABASE_URL=sqlite:///./data/pa_workbench.db
UPLOAD_DIR=./uploads
MEMORY_RECENT_LIMIT=10
```

This mock quickstart is not M2/M3 product acceptance and cannot be used as release proof.

## Real Local Product Setup (M2/M3)

For M2/M3 real product validation, configure PA to use WeKnora and DeepSeek through the
OpenAI-compatible gateway:

```text
KNOWLEDGE_BACKEND=weknora_api
MOCK_MODE=false
CHAT_MODEL_PROVIDER=openai_compatible
MOCK_MODEL_MODE=false
CHAT_MODEL_BASE_URL=<deepseek-compatible-base-url>
CHAT_MODEL_API_KEY=<secret>
CHAT_MODEL_NAME=<deepseek-model>
```

Configure WeKnora with real model credentials:

```text
DEEPSEEK_API_KEY=<secret>
DASHSCOPE_API_KEY=<secret>
```

WeKnora must also have:

```text
KnowledgeQA model: DeepSeek
Embedding model: DashScope
KB embedding_model_id: bound to the DashScope embedding model
DocReader / Redis / vector store: available
```

When the relevant scripts exist, run:

```bash
cd apps/pa-api
python scripts/check_m2_preflight.py
python scripts/check_m2_release.py
python scripts/check_m3_local_product.py
```

Do not print `.env` contents. Report only PASS/FAIL and sanitized configuration names.

Never ask the user for real sensitive department files.

Never print API keys.

## Step 3: Install Backend Dependencies

Recommended:

```bash
cd apps/pa-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `.venv` already exists, reuse it.

On macOS/Linux:

```bash
source .venv/bin/activate
```

## Step 4: Install Frontend Dependencies

```bash
cd apps/pa-web
npm install
```

## Step 5: Start Backend

```bash
cd apps/pa-api
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If port 8000 is busy, use 8001 and report the new URL.

Smoke test:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
```

## Step 6: Start Frontend

```bash
cd apps/pa-web
npm run dev
```

Default URL:

```text
http://localhost:5173
```

If port 5173 is busy, Vite may choose another port. Report the exact URL from terminal output.

## Step 7: Final Report

Report:

```text
Backend URL:
Frontend URL:
Knowledge backend:
Mock mode:
Smoke test results:
Known limitations:
```

## Troubleshooting

### Backend import errors

Run:

```bash
cd apps/pa-api
python -m compileall app
```

### Agent import errors

Run:

```bash
cd .
python -m compileall agent knowledge_engine
```

### Frontend build errors

Run:

```bash
cd apps/pa-web
npm run build
```

### Knowledge backend unavailable

For development-only quickstart, switch to:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
```

For M2/M3 release or local product validation, do not switch to mock. Report the missing
WeKnora, DeepSeek, DashScope, KB, DocReader, Redis, or vector-store gate as BLOCKED.
