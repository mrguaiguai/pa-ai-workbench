---
name: phase3-release-checker
description: Release readiness and safety-check skill for PA AI Workbench phase 3. Use when the user asks to prepare or verify M1/M2/M3 readiness, check WeKnora and real LLM configuration, ensure mock is disabled, inspect git safety, or create/update release checklists.
---

# Phase 3 Release Checker

This skill checks whether a phase 3 milestone is safe to call READY.

## Core Rule

M1 release readiness requires real WeKnora-backed RAG/Wiki capability.

M2 release readiness additionally requires real DeepSeek Chat, WeKnora DeepSeek
KnowledgeQA, DashScope Embedding, Agent real LLM output, and non-mock citations.

M3 release readiness additionally requires a local product runbook and full local
product smoke from empty data.

Do not approve release if:

```text
KNOWLEDGE_BACKEND != weknora_api
MOCK_MODE=true
WeKnora auth/health fails
non-mock citation smoke fails
sensitive files are tracked or staged
```

For M2/M3, also do not approve release if:

```text
CHAT_MODEL_PROVIDER != openai_compatible
MOCK_MODEL_MODE=true
DeepSeek chat smoke fails
DashScope Embedding or KB embedding_model_id check fails
Agent real LLM smoke fails
Wiki real LLM draft/publish/retrieve smoke fails
mock/fallback evidence is counted as release proof
```

## Read First

Read:

```text
docs/archive/legacy-product/PHASE3_SPEC.md
```

Then inspect as needed:

```text
apps/pa-api/.env.example
apps/pa-api/app/config.py
README.md
docs/
scripts/validation/
```

Do not read or print real `.env` values unless the user explicitly asks and it is necessary; never echo secrets in the final report.

## Responsibilities

- Verify M1 release checklist.
- Verify M2/M3 release checklists when the requested scope is M2 or M3.
- Check WeKnora connection, auth, workspace/kb availability.
- Check DeepSeek Chat, WeKnora DeepSeek KnowledgeQA, DashScope Embedding, KB `embedding_model_id`, and vector dimension for M2/M3.
- Check mock mode and backend mode.
- Check RAG/Agent/Wiki smoke outputs, including real LLM smoke outputs for M2/M3.
- Check frontend build.
- Check git tracked/ignored sensitive files.
- Update the corresponding document under `docs/archive/phase3/` only when a
  historical phase task explicitly requires it.

## Release Checklist

Required:

- WeKnora backend reachable.
- Service account configured through environment.
- `KNOWLEDGE_BACKEND=weknora_api`.
- `MOCK_MODE=false`.
- RAG smoke returns `source=weknora_api`.
- Agent smoke saves non-mock citations.
- Wiki smoke proves publish -> retrieve.
- Frontend build passes.
- No secrets or real documents in git.
- README or release docs explain startup and rollback.

M2 additional required:

- `CHAT_MODEL_PROVIDER=openai_compatible`.
- `MOCK_MODEL_MODE=false`.
- DeepSeek chat smoke passes.
- WeKnora KnowledgeQA uses DeepSeek.
- WeKnora Embedding uses DashScope.
- KB has `embedding_model_id` and expected vector dimension.
- Agent real LLM smoke returns real provider/model metadata and non-mock citations.
- Wiki real LLM draft can publish and retrieve `wiki_page` evidence.

M3 additional required:

- Local product runbook works from empty data.
- Status/capability readiness exposes Chat, Embedding, WeKnora, and fallback mode.
- Release mode fails closed when real model/runtime gates are unavailable.
- Golden set and faithfulness regression pass.

## Commands

Use relevant checks:

```bash
cd . && git status --short
cd . && git status --ignored --short
python -m compileall apps/pa-api/app packages/agent-runtime/agent packages/knowledge-engine/knowledge_engine
cd apps/pa-api && python scripts/smoke_weknora_connection.py
cd apps/pa-api && python scripts/smoke_weknora_rag_m1.py
cd apps/pa-api && python scripts/smoke_weknora_agent_m1.py
cd apps/pa-api && python scripts/smoke_weknora_wiki_m1.py
cd apps/pa-api && python scripts/check_m2_preflight.py
cd apps/pa-api && python scripts/smoke_real_chat_model_m2.py
cd apps/pa-api && python scripts/smoke_weknora_agent_real_llm_m2.py
cd apps/pa-api && python scripts/smoke_wiki_real_llm_m2.py
cd apps/pa-api && python scripts/check_m2_release.py
cd apps/pa-api && python scripts/check_m3_local_product.py
cd apps/pa-web && npm run build
```

If scripts do not exist yet, report the missing release gate and fail readiness rather than silently passing.

In spec/skill-only planning turns, do not create or edit checker/smoke scripts; report the
intended gate instead.

## Auto Commit

If release checking creates or updates release docs, checklists, scripts, or spec statuses, and all relevant checks pass, automatically create one task-level commit.

Rules:

1. Commit only release-checker task files.
2. Include the task id in the commit message when available.
3. Use `docs:` for checklist/docs and `test:` for release smoke scripts.
4. Do not push unless the user explicitly asks.
5. If the release decision is `NOT READY` or `BLOCKED`, do not commit status as completed.
6. If unrelated changes are present, leave them unstaged and mention them.
7. If sensitive files are present, stop before commit and report the blocker.

Examples:

```bash
git commit -m "docs: complete P3-M1-F5 release checklist"
git commit -m "test: complete P3-M1-F2 weknora wiki smoke"
```

## Guardrails

- Do not commit or print `.env`.
- Do not stage generated data, uploads, db files, logs, node_modules, or dist.
- Do not count mock smoke tests as release proof.
- Do not count fallback Wiki draft, keyword-only retrieve, old chunks, or fixture-only tests as M2/M3 release proof.
- Do not approve if WeKnora is unreachable unless the release target is explicitly changed away from M1 internal pilot.
- Do not approve M2/M3 if DeepSeek or DashScope gates are unavailable unless the release target is explicitly downgraded.
- Do not push automatically.

## Report Format

```text
Release Scope:
- M1 internal pilot / M2 real LLM gate / M3 local product

Checks:
- WeKnora health: PASS/FAIL
- Config mode: PASS/FAIL
- RAG smoke: PASS/FAIL
- Agent smoke: PASS/FAIL
- Wiki smoke: PASS/FAIL
- DeepSeek chat: PASS/FAIL/N/A
- DashScope embedding: PASS/FAIL/N/A
- Agent real LLM: PASS/FAIL/N/A
- Wiki real LLM: PASS/FAIL/N/A
- M3 local product: PASS/FAIL/N/A
- Frontend build: PASS/FAIL
- Git safety: PASS/FAIL

Decision:
- READY / NOT READY / BLOCKED

Blocking issues:
- ...

Git:
- commit hash, no changes, or blocked reason

Next action:
- ...
```
