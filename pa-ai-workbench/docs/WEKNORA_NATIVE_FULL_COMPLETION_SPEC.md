# PA WeKnora Native Full Completion Spec

> Date: 2026-06-24
>
> Branch: `weknora-first-mvp`
>
> Stage: Native Full Completion
>
> Task prefix: `WNFC-*`
>
> Previous stage source: `docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md`

## 1. Stage Positioning

The previous WNX stage reached the internal production threshold:

```text
12.00 / 15 = 80.0%
```

This stage is stricter. It is not another MVP, visibility pass, or demo layer.
The goal is to finish the remaining WeKnora-native capability surfaces as real
operator workflows in PA, with live API evidence, browser evidence where the UI
is touched, masked credentials, confirmation-gated risky actions, audit records,
and final acceptance evidence.

The user decision for this stage is explicit:

- Web Search is not developed in this stage.
- All other selected native capability areas should be driven to 100% real
  native usability, not mock, demo, or MVP behavior.
- When this stage is complete, PA must be usable on this local machine as a
  real knowledge-base productivity tool for daily work.

## 2. Final Product Exit Criteria

WNFC is complete only when the local PA product can be used as the user's
working knowledge base. Completion means:

- The user can create/select a knowledge base and understand its real native
  readiness.
- The user can ingest local files, URLs/manual content, and at least one real
  external data source into WeKnora-backed knowledge.
- The user can inspect ingestion status, chunks, sync status, and failures.
- The user can search, chat, use AgentQA/custom Agent, and browse Wiki with
  traceable evidence where references are part of the contract.
- The user can organize work with FAQ, tags, favorites, and skills where native
  support exists.
- The user can diagnose model, embedding, rerank, parser, vector store, and
  connector problems from PA without reading raw logs or secrets.
- The user can run controlled MCP actions with confirmation, timeout, audit,
  and safe history.
- The user can stop, restart, and verify the local stack through documented
  commands.
- The product has no fake green states for non-Web-Search core workflows.

This is the practical bar: after WNFC, PA should be something the user can keep
open and use as a local knowledge workbench, not merely a validated prototype.

## 3. Hard Goals

- Reach `14.00 / 14 = 100%` over the WNFC scored native capability groups,
  excluding Web Search from the denominator.
- Convert these WNX `live-partial` groups to WNFC `full-complete`:
  - MCP.
  - Vector store.
  - Model/embedding/rerank/parser.
  - Data sources/connectors, within the current scope that excludes
    credential-bearing Notion/Yuque/Feishu setup by explicit user decision.
  - FAQ/tags/favorites/skills.
- Close residual native-backed admin and mutation gaps in already-live groups
  where WeKnora exposes native support:
  - workspace/knowledge-base admin mutations;
  - advanced chunk operations;
  - custom Agent management;
  - Wiki global maintenance operations.
- Preserve PA's product contract: history, citation, status, audit, masked
  configuration, and recoverable local development workflows.
- Use WeKnora native APIs or native Go extensions first. PA remains a BFF and
  product shell, not a replacement RAG, MCP, connector, vector, parser, or
  model platform.

## 4. WeKnora Source Modification Principle

WNFC uses a `PA-first + controlled native exception lane` rule.

This rule must not be simplified into "only edit PA code" or "freely edit
WeKnora Go code". The correct decision tree is:

| Decision path | Use when | Allowed work | Required result |
| --- | --- | --- | --- |
| `PA-first` | WeKnora already exposes the required native API, event, field, connector, reference, or execution path. | Change PA adapter, BFF, business DB, audit/history/citation layer, and UI only. | Real PA workflow uses existing native capability without duplicating platform logic. |
| `native exception` | WeKnora lacks a required native field, event, reference shape, connector, execution path, or safe API needed for WNFC completion. | Make the smallest necessary WeKnora Go source change, plus the matching PA integration. | Native behavior is tested, deployed locally, and proven through PA live evidence. |
| `blocked` | The gap is a missing third-party API, account, credential, OAuth scope, permission, sample workspace, or operator approval. | Stop the affected capability path and ask the user for the missing item. | No mock, fixture, or no-op replacement is counted as completion. |

Native source changes are allowed only when all of these are true:

1. The task first audits relevant WeKnora routes, handlers, services, types,
   registry/config files, and existing tests.
2. The report explains why PA-only work would create a fake workflow, duplicate
   WeKnora logic, or leave the native capability unusable.
3. The Go change is minimal, traceable, and limited to the missing native
   contract.
4. Native Go tests pass for the affected package or a documented narrower test
   target.
5. If runtime behavior must change, Docker rebuild/recreate or an equivalent
   local runtime validation proves the running WeKnora service uses the change.
6. PA live API evidence, and browser evidence when user-visible, proves the new
   native behavior is usable through PA.
7. The task updates WNFC progress, evidence reports, and final answer with the
   reason for the native exception, touched Go files, tests, runtime validation,
   and PA validation.

If any required API or credential is missing during development, ask the user
for it immediately with the exact provider/module, scope, expected config
location, and post-supply validation plan.

## 5. Explicit Non-Goals

- Do not develop Web Search provider setup, Web Search provider tests, raw web
  search debugging, or AgentQA web-search orchestration in this stage.
- Do not count any Web Search work toward WNFC completion.
- Do not build demo connectors, fake MCP tools, mock model tests, mock vector
  stores, fixture-only browser states, or static green UI.
- Do not treat "configured" as "tested" when a remote provider, connector, MCP
  service, parser, reranker, vector store, or model must actually be called.
- Do not expose raw credential values, provider payloads, private endpoints,
  raw uploaded content, raw vector/index config, local DB contents, logs, or
  prompt payloads.
- Do not silently skip native-source changes when the WeKnora API surface is
  missing. If a required native feature does not exist, either implement a
  small native path with tests and Docker runtime validation, or mark the task
  blocked with an exact native gap.

## 6. Completion States

Use these WNFC states for the new stage:

| State | Score | Meaning |
| --- | ---: | --- |
| `full-complete` | 1.0 | Real PA workflow uses real WeKnora native capability, including list/read/write/test paths that belong to the product contract, with history/status/audit/citation where applicable. |
| `partial` | 0.5 | Real native calls work, but one or more required workflow, mutation, credential, audit, browser, or history/citation contracts are incomplete. |
| `visibility-only` | 0.25 | PA can inspect a native catalog/list/status but cannot run the real workflow. |
| `blocked` | 0 | A real credential/API/runtime/safety/native-source gap prevents completion. |
| `excluded` | N/A | Explicitly outside this stage. Web Search is the only planned excluded capability group; individual task slices can also be `[b]` when the user removes them from the WNFC 100% scope. |

Completion is stricter than the old WNX `live-full` label. A group can have an
old WNX score of `1.0` and still have WNFC residual work if the old report left
native-backed admin or mutation flows in backlog.

## 7. Baseline

Legacy WNX groups: `15`.

WNFC excludes Web Search:

```text
WNFC scored groups = 14
current WNFC score = 14.00 / 14 = 100.0%
target WNFC score = 14.00 / 14 = 100.0%
required score gain = +0.00
```

| Capability group | WNX state | WNFC target | Required move |
| --- | --- | --- | --- |
| System health/status/deployment | `live-full` | `full-complete` | Preserve and revalidate. |
| Workspace/knowledge-base management | `live-full` with residual admin backlog | `full-complete` | Finish safe native CRUD/pin/tag mutations or prove native absence. |
| Document lifecycle | `live-full` | `full-complete` | Preserve and revalidate. |
| Chunk management | `live-full` with advanced backlog | `full-complete` | Resolve content rewrite, generated-question, and search-by-chunk gaps where native support exists. |
| Knowledge-search/RAG | `live-full` | `full-complete` | Preserve current-run evidence and citation mapping. |
| Knowledge-chat/session chat | `live-full` | `full-complete` | Preserve history/citation. |
| AgentQA/custom Agent | `live-full` with custom Agent admin backlog | `full-complete` | Finish copy/update/delete/ownership flows where safe native support exists. |
| Native Wiki | `live-full` with global maintenance backlog | `full-complete` | Finish confirmation-gated global operations. |
| MCP | `live-partial` | `full-complete` | Add configured service, credential, tool/resource, execution, approval, and audit flows. |
| Web Search | `live-partial` | `excluded` | Freeze. Do not develop in this stage. |
| Vector store | `live-partial` | `full-complete` | Add safe test, CRUD/rebind where native ownership allows, and diagnostics. |
| Model/embedding/rerank/parser | `live-full` | `full-complete` | Completed product-grade config, active model/embedding/rerank/parser/storage tests, sample parse validation, and diagnostics. |
| Data sources/connectors | `live-partial` | `full-complete` | Credential-bearing Notion/Yuque/Feishu setup is removed from WNFC 100% scope by user decision; RSS-backed external-source setup/resources/sync/log/delete and RAG evidence from `WNFC-P1-02` and `WNFC-P1-03` define the scoped completion target. |
| FAQ/tags/favorites/skills | `live-partial` | `full-complete` | Add FAQ and organization mutations with history/audit where applicable. |
| History/citation/product shell | `live-full` | `full-complete` | Preserve and expand audit/history filters for new WNFC workflows. |

## 8. Execution Protocol

Every WNFC run must:

1. Work in `/Users/mac/Downloads/WeKnora-main/pa-ai-workbench`.
2. Read this spec.
3. Read `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md`.
4. Read `docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md`.
5. Read `.github/skills/pa-weknora-native-full-completion/SKILL.md`.
6. Read `.github/skills/pa-weknora-native-expansion/SKILL.md` for inherited
   safety rules.
7. Read `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-full-completion/SKILL.md`
   when available.
8. Run `git status -sb` and `git log --oneline -5`.
9. Execute exactly one `WNFC-*` task id per run.
10. Before editing, state in Chinese:
    - task id;
    - task class;
    - planned files;
    - validation method;
    - expected evidence type.
11. Inspect WeKnora native routes, handlers, services, and types before PA code
    changes for every native capability task.
12. Update this spec only after real validation passes or a truthful blocker is
    recorded.

## 9. Required Evidence

WNFC PASS requires current-run evidence, not prior reports alone.

| Evidence type | Required when |
| --- | --- |
| Native source audit | Every native capability task before PA edits. |
| Live API smoke | Every backend/native/BFF task. |
| Live browser proof | Every user-visible frontend workflow. |
| Native Go test | Every native Go source change. |
| Docker runtime validation | Every native Go runtime behavior change that must affect live WeKnora. |
| Credential masking proof | Every credential/provider/connector/MCP/model/vector task. |
| Audit/history proof | Every mutation, execution, or user-visible workflow result. |
| Citation proof | Every answer-producing workflow where references are part of the PA contract. |
| Sensitive scan | Every report/spec/skill/config/provider task. |

The following never counts as WNFC PASS:

- mock providers;
- fixture-only tests;
- static UI states;
- old reports;
- cached browser output;
- "configured" without live testing;
- hidden fallbacks;
- answer text without traceable references when citation is required;
- Web Search work.

## 10. Credential And Approval Rules

Credential-heavy tasks are allowed in WNFC, but only with strict controls:

- Use real operator-provided credentials or real official sandbox credentials.
- Never print, commit, persist in PA DB, or return raw credential values.
- Store only masked summaries and safe status.
- Use confirmation tokens for destructive writes, sync deletion, external tests,
  vector rebinds, MCP tool execution, and Wiki global maintenance.
- Record audit events for every mutation or external execution.
- If real credentials are unavailable, mark the task `blocked`; do not replace
  it with a mock or no-op demo.
- If the user explicitly removes a credential-bearing slice from the WNFC 100%
  scope, mark that task `[b]`, keep the old blocker evidence as historical
  context, and do not request or count those credentials for final readiness.

## 11. Automatic Progress Updates

WNFC tasks are spec-driven and progress-aware. The agent should update task
progress as part of the same task when evidence changes.

Every completed, blocked, or removed WNFC task must update:

1. The task row in Section 12.
2. The progress log in Section 13.
3. The task-specific evidence report under `docs/`.
4. Any affected coverage/acceptance harness documents or scripts.
5. The final answer summary with changed files, validation, evidence type,
   blocker/API requests if any, and next task id.

Status changes are allowed only after evidence:

| New status | Required basis |
| --- | --- |
| `[x]` | Required live/API/browser/native/ops validation passed for that task. |
| `[~]` | A real partial slice landed, but the full task contract is not done. |
| `[!]` | A real API, credential, runtime, safety, or native-source gap blocks completion. |
| `[b]` | The user explicitly removes the slice from WNFC scope. Web Search is already excluded. |

If a task needs an API, SDK, app credential, OAuth setup, provider account,
sample workspace, or native endpoint that is missing, the agent must stop that
capability path and ask the user for the exact missing item. The blocker should
include:

- provider or native module name;
- missing API/credential/scope/endpoint;
- where it is expected to be configured;
- safest minimal value or access level needed;
- what validation will run after the user supplies it.

The agent may continue with read-only audit and planning while waiting, but
must not mark the blocked capability complete.

## 12. Task Board

| ID | Priority | Capability slice | Status | Required evidence |
| --- | --- | --- | --- | --- |
| WNFC-0-01 | Governance | Full-completion spec and skill | [x] | This spec plus repo-local and outer skills; skill validation; diff/sensitive checks. |
| WNFC-0-02 | Governance | Native parity audit excluding Web Search | [x] | Source audit maps WeKnora native routes/services/types to every WNFC target and residual gap. See [WNFC-0-02 parity audit](WEKNORA_NATIVE_FULL_COMPLETION_PARITY_AUDIT_WNFC_0_02.md). |
| WNFC-0-03 | Governance | Credential, approval, and audit foundation | [x] | Shared masked credential/status shape, confirmation token pattern, mutation audit model, and smokes. Live API/browser/audit smoke passed with controlled chunk mutation. See [WNFC-0-03 foundation report](WEKNORA_NATIVE_FULL_COMPLETION_FOUNDATION_WNFC_0_03.md). |
| WNFC-0-04 | Governance | 100% acceptance harness | [x] | Checker excludes Web Search, enforces `14.00/14`, detects mocks/fixtures/stale reports/secrets, accepts explicit `[b]` task-level scope removals, and keeps final mode blocked until all in-scope non-Web-Search work is complete. See [WNFC-0-04 acceptance harness report](WEKNORA_NATIVE_FULL_COMPLETION_ACCEPTANCE_HARNESS_REPORT.md). |
| WNFC-P1-01 | P1 | Data-source connector credential setup | [b] | User removed credential-bearing Notion/Yuque/Feishu connector setup from WNFC 100% scope on 2026-06-24; no credential PASS is claimed or required. See [WNFC-P1-01 credential scope report](WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_CREDENTIAL_BLOCKER_WNFC_P1_01.md). |
| WNFC-P1-02 | P1 | Data-source resources, validation, sync, logs, delete | [x] | Existing/native RSS data-source resources, validation, sync logs, sync/pause/resume/delete pass with confirmation, audit, and browser proof. This is the scoped data-source management target after `WNFC-P1-01` was removed. See [WNFC-P1-02 data source workflow evidence](WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_WORKFLOW_WNFC_P1_02.md). |
| WNFC-P1-03 | P1 | Data-source to KB/RAG evidence loop | [x] | RSS external-source sync creates indexed native knowledge and PA RAG debug/knowledge-chat return traceable native citations scoped to that synced knowledge. This is the scoped external-source RAG target after `WNFC-P1-01` was removed. See [WNFC-P1-03 data source RAG loop evidence](WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_RAG_LOOP_WNFC_P1_03.md). |
| WNFC-P2-01 | P1 | MCP service CRUD and credentials | [x] | PA BFF now performs confirmation-gated native MCP service create/read/update/delete plus credential update/clear with masked metadata and NativeMutationAudit. Does not claim external MCP probe/tool execution. See [WNFC-P2-01 MCP CRUD and credentials evidence](WEKNORA_NATIVE_FULL_COMPLETION_MCP_CRUD_CREDENTIALS_WNFC_P2_01.md). |
| WNFC-P2-02 | P1 | MCP resources/tools/prompts list and read | [b] | User removed MCP service tools/resources/prompts list/read from the current WNFC 100% scope on 2026-06-24; no MCP tool/resource/prompt PASS is claimed or required for this task. See [WNFC-P2-02 MCP tools/resources/prompts scope report](WEKNORA_NATIVE_FULL_COMPLETION_MCP_TOOLS_RESOURCES_PROMPTS_BLOCKER_WNFC_P2_02.md). |
| WNFC-P2-03 | P1 | MCP approval-gated tool execution | [b] | User removed MCP approval-gated tool execution from the current WNFC 100% scope on 2026-06-24; no MCP tool execution PASS is claimed or required. See [WNFC-P2-03 MCP tool execution scope report](WEKNORA_NATIVE_FULL_COMPLETION_MCP_TOOL_EXECUTION_BLOCKER_WNFC_P2_03.md). |
| WNFC-P3-01 | P1 | Product-grade model config migration | [x] | `config/builtin_models.yaml` is mounted into WeKnora, native runtime reports 3 YAML-managed built-in models, PA bridge alignment is live, and Qwen `qwen3-rerank` active check passes. See [WNFC-P3-01 model config source evidence](WEKNORA_NATIVE_FULL_COMPLETION_MODEL_CONFIG_SOURCE_WNFC_P3_01.md). |
| WNFC-P3-02 | P1 | Model, embedding, and rerank active tests | [x] | Native active chat, embedding, and Qwen rerank tests pass with sanitized output: chat `available=true`, embedding returns 1024 dimensions, and rerank returns 1 result. See [WNFC-P3-02 model active tests evidence](WEKNORA_NATIVE_FULL_COMPLETION_MODEL_ACTIVE_TESTS_WNFC_P3_02.md). |
| WNFC-P3-03 | P1 | Parser and storage diagnostics | [x] | Native parser active check reports 7 engines with 4 available, local storage active check passes, PA overview reports parser/storage status, and a sanitized sample markdown document parses/indexes with native chunks and status UI proof. See [WNFC-P3-03 parser/storage diagnostics evidence](WEKNORA_NATIVE_FULL_COMPLETION_PARSER_STORAGE_DIAGNOSTICS_WNFC_P3_03.md). |
| WNFC-P3-04 | P1 | Vector-store full management | [x] | PA BFF now performs confirmation-gated native saved/env test, raw Qdrant test, saved user-store create/update/test/delete, NativeMutationAudit, and browser proof against a disposable Qdrant Docker runtime. Native KB rebind remains surfaced as `native_immutable` instead of faked. See [WNFC-P3-04 vector-store full management evidence](WEKNORA_NATIVE_FULL_COMPLETION_VECTOR_STORE_FULL_MANAGEMENT_WNFC_P3_04.md). |
| WNFC-P4-01 | P2 | FAQ full workflow | [x] | FAQ list/read/create/update/delete/search/import/progress pass through PA BFF against native WeKnora with confirmation, audit, and browser proof. See [WNFC-P4-01 FAQ workflow evidence](WEKNORA_NATIVE_FULL_COMPLETION_FAQ_WORKFLOW_WNFC_P4_01.md). |
| WNFC-P4-02 | P2 | Tags and favorites mutations | [x] | Native tag create/update/delete and favorite add/remove/toggle pass through PA BFF against native WeKnora with confirmation, audit, and browser proof. See [WNFC-P4-02 tags/favorites evidence](WEKNORA_NATIVE_FULL_COMPLETION_TAGS_FAVORITES_WORKFLOW_WNFC_P4_02.md). |
| WNFC-P4-03 | P2 | Native skill management | [x] | Native WeKnora now exposes skill list/read/create/update/delete/test for managed `SKILL.md` files. PA gates create/update/delete/test with `CONFIRM_NATIVE_SKILL_MUTATION`, records `NativeMutationAudit`, and renders live skill status in Capability Center. The test route validates metadata/files only and reports `execution_performed=false`. See [WNFC-P4-03 skill management evidence](WEKNORA_NATIVE_FULL_COMPLETION_SKILL_MANAGEMENT_BLOCKER_WNFC_P4_03.md). |
| WNFC-P5-01 | P2 | KB admin residual closure | [x] | KB create/update/delete/pin pass through PA BFF against native WeKnora with confirmation and audit; tag residuals are already covered by WNFC-P4-02. See [WNFC-P5-01 KB admin residual evidence](WEKNORA_NATIVE_FULL_COMPLETION_KB_ADMIN_RESIDUAL_WNFC_P5_01.md). |
| WNFC-P5-02 | P2 | Chunk advanced residual closure | [x] | Content rewrite refreshes the main chunk content index, generated-question delete is live-proven with a temporary question-generation-enabled KB and real generated-question metadata, and search-by-chunk uses native route or live knowledge-search fallback. See [WNFC-P5-02 chunk advanced residual evidence](WEKNORA_NATIVE_FULL_COMPLETION_CHUNK_ADVANCED_RESIDUAL_BLOCKER_WNFC_P5_02.md). |
| WNFC-P5-03 | P2 | Custom Agent admin residual closure | [x] | Agent create/update/copy/delete/ownership flows pass through PA BFF against native WeKnora with confirmation and audit. See [WNFC-P5-03 custom Agent admin evidence](WEKNORA_NATIVE_FULL_COMPLETION_CUSTOM_AGENT_ADMIN_WNFC_P5_03.md). |
| WNFC-P5-04 | P2 | Wiki global maintenance closure | [x] | Native Wiki rebuild-links, auto-fix, controlled issue create, and issue-status update are confirmation-gated through PA BFF, audited with `NativeMutationAudit`, and live-proven on an isolated temporary wiki-enabled KB. See [WNFC-P5-04 Wiki global maintenance evidence](WEKNORA_NATIVE_FULL_COMPLETION_WIKI_GLOBAL_MAINTENANCE_BLOCKER_WNFC_P5_04.md). |
| WNFC-P6-01 | P0 | Full local productivity browser matrix | [x] | Desktop/mobile browser matrix proves PA is locally usable for daily knowledge-base work with live PA/WeKnora API status, blocker visibility, and acceptance-checker evidence. See [WNFC-P6-01 browser matrix evidence](WEKNORA_NATIVE_FULL_COMPLETION_BROWSER_MATRIX_WNFC_P6_01.md). |
| WNFC-P6-02 | P0 | Final 100% completion report | [x] | Final report proves scoped WNFC completion at `14.00/14 = 100.0%`, Web Search excluded, all in-scope non-Web-Search tasks complete or explicitly `[b]`, and normal plus `--final` acceptance checker mode passing with `final_ready=true`. See [WNFC-P6-02 final completion report](WEKNORA_NATIVE_FULL_COMPLETION_FINAL_BLOCKER_REPORT_WNFC_P6_02.md). |

## 13. Progress Log

| Date | Task id | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 2026-06-24 | WNFC-0-01 | [x] | Governance artifact: full-completion spec plus repo-local and outer skills. | Establishes Web Search exclusion, 14/14 target, local-productivity exit criteria, automatic progress updates, missing-API blocker protocol, and the PA-first plus controlled native exception lane source-modification principle. |
| 2026-06-24 | WNFC-0-02 | [x] | Audit/map: [WNFC-0-02 parity audit](WEKNORA_NATIVE_FULL_COMPLETION_PARITY_AUDIT_WNFC_0_02.md). | Maps non-Web-Search native routes/services/types to PA adapter/BFF/UI surfaces; records PA-first paths, native exception candidates, required external credentials/workspaces, and next task `WNFC-0-03`. No code changes or capability PASS claims. |
| 2026-06-24 | WNFC-0-03 | [x] | Live API/browser plus audit proof: [WNFC-0-03 foundation report](WEKNORA_NATIVE_FULL_COMPLETION_FOUNDATION_WNFC_0_03.md). | Shared confirmation/audit foundation and chunk mutation integration are implemented. Python compile, local audit-service validation, frontend type check, FastAPI route import, and live smoke pass; live smoke records `audit_d2abbad0798f` for a confirmation-token chunk mutation and verifies Library browser DOM. |
| 2026-06-24 | WNFC-0-04 | [x] | Checker execution evidence: [WNFC-0-04 acceptance harness report](WEKNORA_NATIVE_FULL_COMPLETION_ACCEPTANCE_HARNESS_REPORT.md). | Adds `check_weknora_native_full_completion_acceptance.py`; self-test passes, Web Search remains excluded, in-progress mode reports readiness truthfully, and `--final` only passes after all in-scope non-Web-Search tasks and final `14.00/14` proof are complete. |
| 2026-06-24 | WNFC-P1-01 | [b] | Excluded evidence: [WNFC-P1-01 credential scope report](WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_CREDENTIAL_BLOCKER_WNFC_P1_01.md). | User explicitly removed credential-bearing Notion/Yuque/Feishu connector setup from WNFC 100% scope. The old blocker remains documented as historical context, no credential PASS is claimed, and future final-readiness checks must not ask for this credential-bearing slice. |
| 2026-06-24 | WNFC-P1-02 | [x] | Live API/browser/audit evidence: [WNFC-P1-02 data source workflow evidence](WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_WORKFLOW_WNFC_P1_02.md). | PA-first implementation adds native data-source delete adapter/BFF, confirmation-gated sync/pause/resume/delete audit, Capability Center data-source ops panel, and WNFC smoke. Current-run smoke creates a temporary RSS source, validates detail resources/validation/logs, confirms sync/pause/resume/delete, verifies data-source audit events, removes the temporary source, and proves browser DOM. After the `WNFC-P1-01` scope removal, this is the in-scope data-source management proof. |
| 2026-06-24 | WNFC-P1-03 | [x] | Live API plus native citation evidence: [WNFC-P1-03 data source RAG loop evidence](WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_RAG_LOOP_WNFC_P1_03.md). | New P1-03 smoke creates a temporary real RSS source, triggers confirmed PA sync with `NativeMutationAudit`, waits for a new `source=rss` native knowledge item to index, and proves PA RAG debug plus native knowledge-chat return current-run citations scoped to that synced knowledge. After the `WNFC-P1-01` scope removal, the data-source group moves to the scoped `full-complete` target and aggregate score increases to `12.50/14 = 89.3%`. |
| 2026-06-24 | WNFC-P2-01 | [x] | Live API plus audit proof: [WNFC-P2-01 MCP CRUD and credentials evidence](WEKNORA_NATIVE_FULL_COMPLETION_MCP_CRUD_CREDENTIALS_WNFC_P2_01.md). | PA-first implementation adds native MCP create/update/delete and credential update/clear adapter/BFF paths with confirm-token gating, masked credential metadata, and `NativeMutationAudit`. Current-run smoke creates a temporary native MCP service, reads it through PA, updates it to disabled, writes and clears a credential, deletes the service, verifies cleanup, and confirms MCP audit events. P2-02/P2-03 remain open, so aggregate score stays `11.50/14 = 82.1%`. |
| 2026-06-24 | WNFC-P2-02 | [b] | Excluded evidence plus historical blocker evidence: [WNFC-P2-02 MCP tools/resources/prompts scope report](WEKNORA_NATIVE_FULL_COMPLETION_MCP_TOOLS_RESOURCES_PROMPTS_BLOCKER_WNFC_P2_02.md). | User explicitly said to skip MCP service and iterate later. The historical live smoke remains recorded: one native MCP service is visible, but confirmed test returns `partial`, `success=false`, `tools=0`, `resources=0`, and native prompt list/read API is missing. No MCP tool/resource/prompt PASS is claimed. P2-02 no longer blocks WNFC final readiness; P2-03 is separately removed in its own task row. The score from this point was later superseded by P3-04 completion at `13.50/14 = 96.4%`. |
| 2026-06-24 | WNFC-P2-03 | [b] | Excluded evidence plus historical blocker evidence: [WNFC-P2-03 MCP tool execution scope report](WEKNORA_NATIVE_FULL_COMPLETION_MCP_TOOL_EXECUTION_BLOCKER_WNFC_P2_03.md). | User confirmed MCP service execution is temporarily out of scope and should be iterated later. Historical blocker evidence remains recorded: native approval/execution primitives exist, but the configured service initializes as `partial`, `tools=0`, and no real low-risk MCP tool is available. No MCP tool execution PASS is claimed. With P2-02 and P2-03 both `[b]`, the scoped MCP requirement is limited to the already-completed P2-01 CRUD/credential/status slice. The score from this point was later superseded by P3-04 completion at `13.50/14 = 96.4%`. |
| 2026-06-24 | WNFC-P3-01 | [x] | Live API, native Go test, and Docker runtime: [WNFC-P3-01 model config source evidence](WEKNORA_NATIVE_FULL_COMPLETION_MODEL_CONFIG_SOURCE_WNFC_P3_01.md). | Native source audit confirms `config/builtin_models.yaml` / `BUILTIN_MODELS_CONFIG` is the recommended source-of-truth path. PA/native now surface `managed_by=yaml`, `config_source_status`, and `pa_bridge_alignment_status`; `qwen3-rerank` compatible API support is implemented. Docker rebuild/recreate succeeded, source smoke reports `yaml_managed=3` with no missing required model types, and native Qwen rerank active check returns `available=true`. Score remains `11.50/14 = 82.1%` until P3-02/P3-03 close the broader group. |
| 2026-06-24 | WNFC-P3-02 | [x] | Live API: [WNFC-P3-02 model active tests evidence](WEKNORA_NATIVE_FULL_COMPLETION_MODEL_ACTIVE_TESTS_WNFC_P3_02.md). | Native source audit confirms WeKnora already exposes Admin active-test endpoints for chat, embedding, and rerank through `/api/v1/initialization/*`. The PA smoke calls those native endpoints with real local provider config and sanitized output. Current-run evidence: chat `available=true`, embedding `available=true` with dimension `1024`, and Qwen rerank `available=true` with one returned result. No UI or Go source changed in this task. Score remains `11.50/14 = 82.1%` until P3-03 closes parser/storage diagnostics for the broader group. |
| 2026-06-24 | WNFC-P3-03 | [x] | Live API/browser: [WNFC-P3-03 parser/storage diagnostics evidence](WEKNORA_NATIVE_FULL_COMPLETION_PARSER_STORAGE_DIAGNOSTICS_WNFC_P3_03.md). | Native source audit confirms WeKnora exposes Viewer parser/storage status routes and Admin active-check routes. Current-run smoke calls native parser/storage active checks, verifies PA `/api/model/native/overview`, uploads a sanitized markdown sample through PA to native WeKnora, waits for `status=indexed` and `parse_status=completed`, verifies `chunks=1`, deletes the temporary document, and confirms Capability Center parser/storage status UI. Model/embedding/rerank/parser is now WNFC full-complete; score increases to `12.00/14 = 85.7%`. |
| 2026-06-24 | WNFC-P3-04 | [x] | Live API/browser plus Docker runtime plus audit proof: [WNFC-P3-04 vector-store full management evidence](WEKNORA_NATIVE_FULL_COMPLETION_VECTOR_STORE_FULL_MANAGEMENT_WNFC_P3_04.md). | Native source audit confirms WeKnora exposes vector-store CRUD/test APIs, masks list/detail responses, treats env stores as read-only, excludes `postgres`/`sqlite` from saved user-store types, and makes KB `vector_store_id` immutable after creation. PA now records `NativeMutationAudit` for confirmed saved/env store tests, raw Qdrant test, saved user-store create/update/delete, and renders vector-store live status in Capability Center. Current-run smoke uses disposable Qdrant Docker runtime `1.18.2`, proves raw test plus user-store create/update/test/delete, cleans up the temporary user store, and keeps raw config out of API/audit/report output. Vector store is now WNFC full-complete; score increases to `13.50/14 = 96.4%`. |
| 2026-06-24 | WNFC-P4-01 | [x] | Live API/browser plus audit proof: [WNFC-P4-01 FAQ workflow evidence](WEKNORA_NATIVE_FULL_COMPLETION_FAQ_WORKFLOW_WNFC_P4_01.md). | Native source audit confirms WeKnora exposes FAQ list/read/create/update/delete/search/import/progress routes for FAQ-type KBs. PA now exposes confirmation-gated FAQ BFF endpoints, records `NativeMutationAudit` for create/update/import/delete, and keeps raw questions/answers out of responses and audit summaries. Current-run smoke creates a validation FAQ KB with inherited embedding config, proves create/read/update/search/import-progress/delete through PA, verifies audit events and Capability Center `faq_status: live`, then deletes the validation KB. FAQ is complete; the broader FAQ/tags/favorites/skills group remains partial until P4-02/P4-03, so score remains `12.00/14 = 85.7%`. |

| 2026-06-24 | WNFC-P4-02 | [x] | Live API/browser plus audit proof: [WNFC-P4-02 tags/favorites evidence](WEKNORA_NATIVE_FULL_COMPLETION_TAGS_FAVORITES_WORKFLOW_WNFC_P4_02.md). | Native source audit confirms WeKnora exposes KB tag list/create/update/delete routes and user favorite list/add/remove routes. PA now exposes confirmation-gated tag and favorite BFF endpoints, records `NativeMutationAudit`, and renders Capability Center `tag_mutations: live` plus `favorite_mutations: live`. Current-run smoke creates a validation KB, proves tag create/update/delete and favorite add/remove/toggle through PA, verifies audit events, then cleans up the KB. Favorite update is native-absent because favorites have no mutable fields; PA toggle maps to native add/remove. The broader FAQ/tags/favorites/skills group remains partial until P4-03, so score remains `12.00/14 = 85.7%`. |
| 2026-06-24 | WNFC-P4-03 | [x] | Live API/browser plus audit proof: [WNFC-P4-03 skill management evidence](WEKNORA_NATIVE_FULL_COMPLETION_SKILL_MANAGEMENT_BLOCKER_WNFC_P4_03.md). | Native source patch adds Viewer+ skill read and Admin+ managed `SKILL.md` create/update/delete/test routes. PA now exposes confirmation-gated skill BFF endpoints, records `NativeMutationAudit` for create/update/test/delete, redacts raw instructions from PA summaries, and renders `skill_management_status: live` plus `skill_mutations: live` in Capability Center. Current-run smoke blocks a bad token, creates/reads/updates/tests/deletes a temporary skill, verifies audit events, and proves browser DOM. Skill test is metadata/file validation only with `execution_performed=false`. FAQ/tags/favorites/skills is WNFC full-complete. |
| 2026-06-24 | WNFC-P5-01 | [x] | Live API/browser plus audit proof: [WNFC-P5-01 KB admin residual evidence](WEKNORA_NATIVE_FULL_COMPLETION_KB_ADMIN_RESIDUAL_WNFC_P5_01.md). | Native source audit confirms WeKnora exposes KB create/update/delete and per-user pin routes, plus tag routes already completed by WNFC-P4-02. PA now exposes confirmation-gated KB admin BFF endpoints, records `NativeMutationAudit` for create/update/pin/delete, and renders Workspace/KB mutation readiness in Capability Center. Current-run smoke creates an isolated validation KB, updates it, pins it, verifies audit events, deletes it, and proves browser DOM. Workspace/KB score was already `live-full`, so aggregate score remains `12.00/14 = 85.7%`. |
| 2026-06-24 | WNFC-P5-02 | [x] | Live API/browser plus audit proof: [WNFC-P5-02 chunk advanced residual evidence](WEKNORA_NATIVE_FULL_COMPLETION_CHUNK_ADVANCED_RESIDUAL_BLOCKER_WNFC_P5_02.md). | Native `UpdateChunk` refreshes the main chunk content index by source id when content changes, PA exposes confirmation-gated chunk content rewrite with audit, and Library renders edit/save controls. Generated-question delete is now live-proven by creating a temporary question-generation-enabled KB, uploading a real temporary document, waiting for WeKnora-generated `generated_questions` metadata, deleting one generated question through PA, and verifying audit/events. Search-by-chunk uses native route when deployed and a live `/knowledge-search` fallback when the current runtime lacks that route. Capability Center shows `content_rewrite_status: live`, `generated_question_seed_status: live`, `generated_question_delete_status: live`, and `search_by_chunk_status: live`. |
| 2026-06-24 | WNFC-P5-03 | [x] | Live API/browser plus audit proof: [WNFC-P5-03 custom Agent admin evidence](WEKNORA_NATIVE_FULL_COMPLETION_CUSTOM_AGENT_ADMIN_WNFC_P5_03.md). | Native source audit confirms WeKnora exposes custom Agent create/update/delete/copy routes with `OwnedAgentOrAdmin` and copy-owned-by-caller semantics. PA now exposes confirmation-gated custom Agent create/update/copy/delete BFF endpoints, records `NativeMutationAudit` capability `custom_agent`, forces Web Search disabled in Agent mutation payloads, and renders Agent admin readiness in Analysis. Current-run smoke blocks a bad token, creates an isolated custom Agent, updates it, copies it, deletes both custom Agents, verifies audit events, and proves browser DOM. AgentQA/custom Agent score was already `live-full`, so aggregate score remains `12.00/14 = 85.7%`. |
| 2026-06-25 | WNFC-P5-04 | [x] | Live API plus audit proof: [WNFC-P5-04 Wiki global maintenance evidence](WEKNORA_NATIVE_FULL_COMPLETION_WIKI_GLOBAL_MAINTENANCE_BLOCKER_WNFC_P5_04.md). | Native source patch adds owner/admin `POST /wiki/issues`, `CreateIssue`, and KB-scoped `UpdateIssueStatusForKB`. PA exposes confirmation-gated `CREATE_NATIVE_WIKI_ISSUE`, records `weknora_wiki_create_issue`, and keeps rebuild-links, auto-fix, and issue-status under `NativeMutationAudit`. Current-run smoke creates an isolated temporary wiki-enabled KB and page, rejects a bad token, runs rebuild-links and auto-fix, creates a real native issue, resolves it, verifies audit events, and cleans up. Wiki global maintenance is now complete; scoped score remains `14.00/14 = 100.0%`, with final readiness still waiting only on WNFC-P6-02. |
| 2026-06-24 | WNFC-P6-01 | [x] | Live API, live browser, and checker execution: [WNFC-P6-01 browser matrix evidence](WEKNORA_NATIVE_FULL_COMPLETION_BROWSER_MATRIX_WNFC_P6_01.md). | Current-run matrix starts temporary PA backend/frontend services, validates `/api/status`, `/api/model/status`, `/api/native/status`, `/api/native-audit/events`, runs the WNFC acceptance checker, and opens Home, Library, Analysis, RAG debug, Wiki, History, and Capability Center in desktop and mobile Chrome. Browser proof reports `routes=7`, `viewport_checks=14`, `overflow=0`, `visible_overlap=0`, and visible blocker/status text for MCP/vector/skills as of that run. This task proves local product usability but does not by itself decide final readiness. |
| 2026-06-25 | WNFC-P6-02 | [x] | Checker execution evidence plus live API/browser evidence summary: [WNFC-P6-02 final completion report](WEKNORA_NATIVE_FULL_COMPLETION_FINAL_BLOCKER_REPORT_WNFC_P6_02.md). | Final scoped score is `14.00/14 = 100.0%`, all in-scope non-Web-Search capability tasks are complete or explicitly `[b]`, normal and `--final` acceptance checker modes pass with `final_ready=true`, and WNFC-P6-01 remains the local productivity browser matrix hook. Credential-bearing data-source connector setup and MCP service execution/list-read slices are `[b]` and no longer counted. No Web Search work was added or counted. |

## 14. Task Cards

### WNFC-0-01: Full-completion spec and skill

- Goal: create this spec and the paired Codex skill that will drive WNFC work.
- Editable files:
  - `docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md`;
  - `.github/skills/pa-weknora-native-full-completion/SKILL.md`;
  - `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-full-completion/SKILL.md`.
- Forbidden: product code, `.env`, DBs, logs, caches, screenshots, uploads,
  `node_modules`, `dist`, and unrelated reports.
- Acceptance: skill frontmatter validates, template placeholders are removed, Web Search is
  excluded, WNFC task board exists, local productivity exit criteria exist, and
  sensitive scan passes. Automatic progress update rules and missing-API
  blocker rules must be present. The WeKnora source-modification principle must
  be explicit enough to prevent both "only PA code" and "freely edit Go"
  interpretations.
- Evidence type: governance artifact.

### WNFC-0-02: Native parity audit excluding Web Search

- Goal: build a route/service/type parity map for every WNFC group.
- Scope: MCP, vector store, model/embedding/rerank/parser, data sources,
  FAQ/tags/favorites/skills, and residual KB/chunk/Agent/Wiki admin flows.
- Forbidden: code changes or PASS claims.
- Acceptance: report names native files, API routes, missing native paths,
  required credentials, PA files to touch, and first implementation task.
- Evidence type: audit/map.

### WNFC-0-03: Credential, approval, and audit foundation

- Goal: create shared safety infrastructure before high-risk flows.
- Scope: masked credential status, confirmation token convention, mutation
  audit model, timeout/error classes, and UI affordances for dangerous actions.
- Acceptance: at least one low-risk mutation or test path uses the shared
  pattern end to end.
- Evidence type: live API/browser plus audit proof.

### WNFC-0-04: 100% acceptance harness

- Goal: prevent false 100% claims.
- Scope: parse WNFC spec, task reports, coverage math, Web Search exclusion,
  sensitive patterns, mock/fixture/stale evidence, and browser hook inventory.
- Acceptance: checker fails if any non-Web-Search target group remains partial,
  visibility-only, blocked, or unreported.
- Evidence type: checker execution.

### WNFC-P1: Data-source connector completion

- Goal: keep the in-scope data-source connector workflow `full-complete`
  through real RSS-backed external-source workflows.
- Required: resource listing, validation, sync, pause/resume, logs, deletion,
  browser workflow, audit, and KB/RAG evidence for the scoped external source.
- Scope rule: credential-bearing Notion/Yuque/Feishu setup is `[b]` by user
  decision and must not block WNFC 100%. Do not substitute fake credentials or
  claim a credential-bearing PASS.

### WNFC-P2: MCP completion

- Goal: make configured MCP services usable from PA with controlled execution.
- Required: service CRUD, credential masking, resources/tools/prompts read,
  at least one low-risk tool execution, confirmation, timeout, audit, and
  history/status integration.
- Blocker rule: no configured service means blocked, not complete.

### WNFC-P3: Model, vector, parser, and storage completion

- Goal: make operator diagnostics real enough to explain and fix RAG quality.
- Required: product-grade built-in model config, active chat/embedding/rerank
  tests, parser sample tests, storage/vector tests, vector rebind/CRUD where
  ownership allows, masked output, and browser diagnostics.
- Blocker rule: provider keys or parser/storage runtime gaps must be recorded
  as blockers with exact next actions.

### WNFC-P4: FAQ, tags, favorites, and skills completion

- Goal: turn organization primitives into real daily-use workflows.
- Required: FAQ workflows, tag mutations, favorite toggles, native skill
  management or exact native blockers, plus audit/browser evidence.

### WNFC-P5: Residual native admin completion

- Goal: close native-backed backlog left inside old WNX `live-full` groups.
- Required: KB admin residuals, chunk advanced operations, custom Agent admin,
  and Wiki global maintenance, each with native-source audit, confirmation, and
  audit records.
- Blocker rule: if native support is absent, record exact files/routes audited
  and decide whether a narrow native Go extension is required.

### WNFC-P6: Final local productivity acceptance

- Goal: prove that every non-Web-Search WNFC target is complete and PA can be
  used locally as the user's working knowledge base.
- Required: live API smokes, browser matrix, native Go test evidence where
  applicable, acceptance harness, final report, and handoff prompt.
- Acceptance: final score is `14.00 / 14 = 100.0%`.

## 15. Validation Commands

Run these for governance tasks:

```bash
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/.github/skills/pa-weknora-native-full-completion
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-full-completion
git diff --check -- docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md .github/skills/pa-weknora-native-full-completion/SKILL.md
```

For product tasks, add task-specific live API, browser, native Go, Docker, and
sensitive-output checks before any spec status moves to `[x]`.
