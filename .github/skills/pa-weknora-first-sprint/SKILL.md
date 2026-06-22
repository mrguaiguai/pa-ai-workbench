---
name: pa-weknora-first-sprint
description: Repo-local mirror for executing PA AI Workbench WeKnora-first five-day sprint tasks from docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md.
---

# PA WeKnora-First Sprint Skill Mirror

This repo-local mirror preserves the sprint execution rules inside the
`pa-ai-workbench` git history. The active external skill may also exist at:

```text
/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-first-sprint/SKILL.md
```

If the external skill and this repo-local mirror diverge, obey the stricter
rule and update the mirror in the same task when the change affects sprint
execution.

## Source Of Truth

Default repo:

```text
/Users/mac/Downloads/WeKnora-main/pa-ai-workbench
```

Read these files before every sprint task:

1. `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`
2. `docs/PA_EXISTING_WORK_REVIEW_FOR_WEKNORA_FIRST.md` when prior PA work matters
3. `.github/skills/pa-weknora-first-sprint/SKILL.md`
4. The external `.agents` skill when available

Run `git status -sb` and `git log --oneline -5` before editing.

## One Task Rule

Every sprint run must use exactly one `WF-*` task id.

- User-specified `WF-*` id wins.
- Otherwise choose the earliest unfinished P0 task.
- Do not move to P1 while P0 is unfinished unless the user explicitly says so.
- Treat P2 as backlog unless the user scopes a narrow read-only or jump slice.
- Split oversized work into a new explicit task card instead of silently doing
  multiple tasks.

Before editing, state in Chinese:

1. `WF-*` task id
2. Classification: WeKnora native capability, PA product shell, or PA-native professional backlog
3. Planned files to edit
4. Validation command/API/browser check
5. Expected PASS evidence type: live API, live browser, audit/map, blocked, or backlog

## WeKnora-First Rule

For native capability tasks, inspect WeKnora native source/API before changing
PA code. Prefer WeKnora native modules for general knowledge ingestion,
retrieval, Wiki, AgentQA, custom Agent, MCP, web search, and vector store
behavior. PA should own product shell, adapters, history, reports, status, and
citation/evidence mapping.

Do not self-implement a parallel general RAG, Wiki, Agent, parser, chunker,
embedding, or vector-store subsystem when WeKnora has a native path.

## PASS Rules

PASS requires current evidence from the real PA backend/frontend or PA API,
real WeKnora native capability, and real non-mock model/embedding runtime when
the task depends on model or embedding behavior.

Do not count these as PASS:

- mock backend, mock model, or mock embedding
- fixture-only proof
- static UI or demo page
- old report, old cache, or stale browser state
- hidden fallback
- partial native response without the required citation/status contract

If live capability is unavailable, mark the task blocked or backlog with cause
and next step. Do not create mock data to turn the task green.

## Validation Rules

For frontend tasks:

- Run build/type checks when feasible.
- Use browser validation for affected pages.
- Confirm visible status distinguishes real, mock, fallback, partial, blocked,
  and backlog states.

For backend tasks:

- Validate through API calls or smoke scripts.
- Prefer `backend/.venv/bin/python` for PA scripts.
- Keep `/health`, `/api/status`, and `/api/model/status` separate because
  WeKnora connectivity, chat model readiness, and embedding readiness can
  differ.

Update `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md` status only after validation or
a real blocked/backlog decision.

## Safety And Commit Rules

Never print, write, stage, or commit secrets or runtime artifacts:

- `.env` values, API keys, service tokens, passwords, private keys
- private endpoints or provider payloads
- uploaded file bodies, raw prompts, local database contents, logs, caches
- uploads, `node_modules`, `dist`, screenshots, generated runtime files

Use precise staging paths. Do not use broad staging such as `git add docs` when
unrelated untracked docs exist. Commit only current-task files. Do not push
unless the user explicitly asks.

## Required Task Output

Summarize changed files, validation results, live evidence or blocked/backlog
reason, risks, current branch and commit, and whether unrelated untracked files
remained untouched.
