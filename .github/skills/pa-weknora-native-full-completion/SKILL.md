---
name: pa-weknora-native-full-completion
description: Use this skill for PA AI Workbench WeKnora Native Full Completion work in repository root, especially WNFC-* tasks that must drive non-Web-Search WeKnora native capabilities from partial/backlog to 100% real local productivity-tool completion with live API/browser/native evidence, masked credentials, confirmation-gated mutations, automatic spec progress updates, missing-API blocker prompts, audit/history/citation integration, and no demo or MVP shortcuts.
---

# PA WeKnora Native Full Completion

Use this skill for every `WNFC-*` task in the Native Full Completion stage.
This stage excludes Web Search and targets a PA product that is locally usable
as the user's working knowledge-base productivity tool.

Default cwd:

```text
repository root
```

## Source Of Truth

At the start of each task:

1. Read `docs/archive/wnfc/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md`.
2. Read `docs/archive/wnx/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md`.
3. Read `docs/archive/wnx/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md`.
4. Read `.github/skills/pa-weknora-native-full-completion/SKILL.md`.
5. Read `.github/skills/pa-weknora-native-expansion/SKILL.md`.
6. Read `.agents/skills/pa-weknora-native-full-completion/SKILL.md` when available.
7. Run `git status -sb` and `git log --oneline -5`.

If this skill and the outer mirror diverge, obey the stricter rule and repair
the divergence in a governance task.

## Task Binding

- Execute exactly one `WNFC-*` task id per run.
- If the user names a task id, use that id.
- If the user says continue, choose the earliest unfinished WNFC task in this
  order: `WNFC-0`, `WNFC-P1`, `WNFC-P2`, `WNFC-P3`, `WNFC-P4`, `WNFC-P5`,
  `WNFC-P6`.
- Do not develop Web Search in WNFC unless the user explicitly changes scope.
- Exclude Web Search from WNFC coverage math and task selection.

## Classify Before Editing

Before modifying files, state in Chinese:

1. Task id.
2. Task type:
   - WeKnora native capability接入
   - PA BFF/business DB/history/citation/audit
   - PA product shell
   - credential/approval/security foundation
   - validation/ops/deployment
   - native-source patch/runtime validation
3. Planned files.
4. Validation method.
5. Expected PASS evidence type: live API, live browser, live service, native Go
   test, Docker runtime, audit/map, blocked, or excluded.

## Native Source First

For native capability tasks, inspect WeKnora routes, handlers, services, and
types before PA edits. Use `rg` first. Relevant areas include:

- MCP: `internal/handler/mcp_service.go`, `internal/application/service/mcp_service.go`.
- Vector store: `internal/handler/vectorstore.go`, `internal/application/service/vectorstore*.go`, `internal/types/vectorstore.go`.
- Model/config/parser/storage: relevant `internal/handler/*`, `internal/application/service/*`, `internal/types/*`, `config/builtin_models.yaml.example`, and docs.
- Data source/connectors: relevant `internal/datasource/**`, connector registry, handlers, services, and types.
- FAQ/tag/favorite/skill: relevant handlers, services, and types found by `rg`.
- Residual KB/document/chunk/Agent/Wiki admin flows: inspect matching native
  files before deciding whether PA can finish the workflow.

Then inspect PA adapter/product files such as:

- `packages/knowledge-engine/knowledge_engine/backends/weknora_api_backend.py`
- `apps/pa-api/app/api/*`
- `apps/pa-api/app/services/*`
- `apps/pa-api/app/models.py`
- `packages/agent-runtime/agent/orchestrator.py`
- `packages/agent-runtime/agent/tools/registry.py`
- `apps/pa-web/src/pages/*`

Do not build a PA-owned replacement for a WeKnora native platform feature. If
the native API is missing, implement or propose the smallest native Go path and
validate it with native tests plus Docker runtime proof before claiming PASS.

## Source Modification Principle

Use `PA-first + controlled native exception lane`.

Do not interpret WNFC as "only edit PA code". Also do not freely edit WeKnora
Go source. Choose the path deliberately:

- `PA-first`: when WeKnora already exposes the required native API, event,
  field, connector, reference, or execution path, change only PA adapter, BFF,
  business DB, audit/history/citation, and UI.
- `native exception`: when WeKnora lacks a required native field, event,
  reference shape, connector, execution path, or safe API, make the smallest
  necessary Go change and the matching PA integration.
- `blocked`: when the gap is a missing third-party API, account, credential,
  OAuth scope, permission, sample workspace, or operator approval, stop the
  affected path and ask the user for the exact missing item.

Every native-source patch must report:

- why PA-only work would be a fake workflow or duplicate WeKnora logic;
- touched Go files and the missing native contract they satisfy;
- focused native Go test result;
- Docker rebuild/recreate or equivalent runtime validation when behavior must
  change in the running service;
- PA live API validation and browser validation when user-visible.

## Completion Bar

Only `full-complete` can close a WNFC target task. Completion requires a real
PA workflow plus real WeKnora native capability, including required
list/read/write/test, status, browser, audit, and history/citation contracts.

Never mark complete from mock providers, fixture-only tests, static UI states,
old reports, cached browser output, configured-but-untested providers, hidden
fallbacks, or answer text without traceable references when citation is
required.

## Automatic Progress Updates

When evidence changes, update progress in the same task. Do not leave the spec
stale for the next agent.

For every completed, partial, blocked, or removed task, update:

1. The task row in `docs/archive/wnfc/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md`.
2. The progress log in the same spec.
3. The task evidence report under `docs/`.
4. Any affected coverage ledger, acceptance harness, validation script, or
   final report.
5. The final answer with changed files, validation, evidence type, risks,
   blocker/API requests, and next task id.

Allowed status moves:

- `[x]`: required current-run evidence passed.
- `[~]`: a real partial slice landed, but full contract remains.
- `[!]`: a real API, credential, runtime, safety, or native-source gap blocks.
- `[b]`: the user explicitly removes the slice from scope.

## Missing API And Credential Protocol

If a task needs an API, SDK, OAuth app, provider key, workspace, account, scope,
native endpoint, or sample data that is missing, stop the affected capability
path and ask the user for the missing item.

The blocker must name:

- provider or native module;
- exact missing API/credential/scope/endpoint;
- expected config location;
- minimal access level needed;
- validation that will run after the user supplies it.

Continue with read-only audit if useful, but do not substitute a demo or mark
the blocked capability complete.

## Credential And Safety Rules

- Show only masked/configured/status/test summaries.
- Never print or commit `.env` values, API keys, service tokens, passwords,
  private endpoints, private key blocks, raw uploaded bodies, local DB contents,
  logs, caches, raw prompts, provider payloads, raw vector data, or raw
  connector config.
- Do not store WeKnora authoritative chunks, vectors, provider payloads, or
  credentials in PA business DB.
- Use confirmation tokens for destructive writes, external tests, MCP tool
  execution, sync deletion, vector rebind, and Wiki global maintenance.
- Record audit/history entries for mutations and external executions.

## Validation

- Backend tasks require live PA/WeKnora API or service smoke, or a recorded
  blocker.
- Frontend tasks require browser validation.
- Native Go changes require focused native tests and Docker runtime validation
  when the running WeKnora behavior must change.
- Credential/provider/config tasks require masked-output checks and sensitive
  scans.
- Final completion requires the WNFC acceptance harness and final report to
  prove `14.00 / 14 = 100.0%` excluding Web Search, plus a local productivity
  browser matrix that proves PA can be used as the user's working knowledge
  base.

## Staging And Output

- Stage only current-task files with explicit paths.
- Do not stage `.env`, databases, logs, caches, uploads, `node_modules`, `dist`,
  screenshots, or unrelated reports.
- Keep the protected Phase-5 dialogue retrospective untouched and unstaged
  unless the user explicitly changes scope.
- Do not push or merge unless explicitly asked.

End each task with changed files, validation results, evidence type, risks, and
the next useful `WNFC-*` task.
