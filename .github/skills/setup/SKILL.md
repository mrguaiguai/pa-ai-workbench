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
pa-ai-workbench/DEV_SPEC.md
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
cd pa-ai-workbench/backend
```

If `.env` does not exist, create it from `.env.example`.

Default MVP config:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
DATABASE_URL=sqlite:///./data/pa_workbench.db
UPLOAD_DIR=./uploads
MEMORY_RECENT_LIMIT=10
```

Never ask the user for real sensitive department files.

Never print API keys.

## Step 3: Install Backend Dependencies

Recommended:

```bash
cd pa-ai-workbench/backend
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
cd pa-ai-workbench/frontend
npm install
```

## Step 5: Start Backend

```bash
cd pa-ai-workbench/backend
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
cd pa-ai-workbench/frontend
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
cd pa-ai-workbench/backend
python -m compileall app
```

### Agent import errors

Run:

```bash
cd pa-ai-workbench
python -m compileall agent knowledge_engine
```

### Frontend build errors

Run:

```bash
cd pa-ai-workbench/frontend
npm run build
```

### Knowledge backend unavailable

For MVP, switch to:

```text
KNOWLEDGE_BACKEND=mock
MOCK_MODE=true
```

