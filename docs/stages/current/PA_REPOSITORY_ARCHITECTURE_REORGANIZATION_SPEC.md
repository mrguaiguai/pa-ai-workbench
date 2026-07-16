# PA Repository Architecture Reorganization Spec

> Date: 2026-07-14
>
> Stage: PA Repository Architecture Reorganization
>
> Task prefix: `PAR-*`
>
> Repository root: current checkout root
>
> Product: PA AI Workbench

## 1. Stage Positioning

This stage reorganizes the combined PA AI Workbench and WeKnora checkout into
one PA-first monorepo. It changes repository ownership, paths, documentation,
build contexts, and validation entry points without changing product behavior.

The intended product relationship is:

```text
PA AI Workbench
├── PA product shell, BFF, history, citation, audit, and workflows
└── WeKnora native platform runtime
```

PA is the product. WeKnora is the native knowledge and Agent platform used by
PA. The final repository must make that relationship obvious from its name,
root README, directory tree, build entry points, and release artifacts.

## 2. Verified Starting Baseline

The 2026-07-14 read-only audit found these structural risks:

1. The checkout originally had an outer Git repository at its root.
2. The legacy PA product subtree originally contained a nested Git repository.
3. Both repositories use the same GitHub PA repository as `origin`, while the
   outer working tree also contains the full WeKnora source tree.
4. The outer repository tracked the legacy PA product files while the nested
   repository tracked the same files independently.
5. The physical working tree combines an outer branch state with a newer nested
   PA branch state. A clean nested status therefore appears as many modified or
   untracked PA files from the outer repository.
6. PA startup scripts existed in duplicate outer and legacy product paths.
7. Product specs, upstream platform docs, acceptance reports, runtime artifacts,
   and personal project materials are mixed across the outer and nested trees.
8. The current outer folder name still presents WeKnora as the project even
   though the GitHub remote and product direction are PA AI Workbench.

No canonical commit is selected by this governance task. `PAR-0-02` and
`PAR-P0-01` must determine and freeze the coherent PA plus native-runtime
baseline before any relocation.

## 3. Goals

- Establish one canonical Git root and one authoritative branch lineage.
- Make PA AI Workbench the repository root product.
- Move the controlled WeKnora fork/runtime beneath `platform/weknora/`.
- Promote PA API, Web, Agent, and Knowledge Engine modules into first-class
  root workspaces.
- Preserve native WeKnora ownership for RAG, Wiki, AgentQA, MCP, Web Search,
  model, parser, vector, connector, and related platform internals.
- Preserve Git history, current validated behavior, citation/history/audit
  contracts, and native patches.
- Consolidate infrastructure, scripts, tests, skills, and documentation.
- Produce one clean-clone build/start/acceptance path.
- Leave no nested `.git`, hidden source tree, ambiguous build context, or fake
  compatibility state.

## 4. Non-Goals

- Do not add product features, SSO, multi-tenancy, packaging, or new knowledge
  content in this stage.
- Do not rewrite PA Python/React or WeKnora Go code for style during pure moves.
- Do not replace WeKnora native capabilities with PA-owned implementations.
- Do not rewrite published Git history, delete branches, remove a nested
  `.git`, or discard working-tree changes without explicit user approval and
  verified recoverability.
- Do not delete personal project materials, historical reports, or runtime data
  as part of cleanup. Relocate or exclude them only through an explicit task.
- Do not claim completion from a tidy directory tree alone. Builds, live
  services, native workflows, and a clean clone must still pass.

## 5. Target Repository Architecture

```text
PA-AI-Workbench/
├── apps/
│   ├── pa-api/                  # PA FastAPI BFF and business DB
│   └── pa-web/                  # PA React product shell
├── packages/
│   ├── agent-runtime/           # PA workflow/orchestration distribution
│   │   ├── pyproject.toml
│   │   └── agent/               # preserve the Python import package name
│   └── knowledge-engine/        # PA adapter/evidence distribution
│       ├── pyproject.toml
│       └── knowledge_engine/    # preserve the Python import package name
├── platform/
│   └── weknora/                 # controlled WeKnora native runtime source
│       ├── UPSTREAM.md
│       └── PA_PATCHES.md
├── infra/
│   ├── compose/
│   ├── docker/
│   ├── helm/
│   ├── env/
│   └── reverse-proxy/
├── scripts/
│   ├── dev/
│   ├── ops/
│   ├── release/
│   └── validation/
├── tests/
│   ├── backend/
│   ├── frontend/
│   ├── native/
│   └── acceptance/
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── operations/
│   ├── stages/
│   ├── evidence/
│   ├── handoff/
│   └── archive/
├── knowledge-packs/
│   ├── schema/
│   └── examples/
├── .github/
│   ├── workflows/
│   └── skills/
├── compose.yaml
├── Makefile
├── README.md
├── PRODUCT_SPEC.md
├── ARCHITECTURE.md
├── LICENSE
└── THIRD_PARTY_NOTICES.md
```

`knowledge-packs/examples/` may contain sanitized examples only. Real
department documents, local databases, uploads, vectors, and credentials remain
outside Git.

The hyphenated distribution directories under `packages/` must not replace the
existing Python import names. Establish installable workspace metadata before
removing current path injection. Once root PA `packages/` exists, native Docker
build contexts must be rooted at `platform/weknora/`; otherwise native
Dockerfiles that copy `packages/` can silently copy the PA distributions.

## 6. Ownership Boundaries

| Area | Owner | Allowed responsibility | Forbidden responsibility |
| --- | --- | --- | --- |
| `apps/pa-web` | PA | Product navigation, dialogue, library, Wiki, history, capability UX | Direct raw calls to WeKnora or secret-bearing configuration |
| `apps/pa-api` | PA | BFF normalization, business DB, confirmation, audit, history, citation, safe status | Reimplementation of WeKnora platform internals |
| `packages/agent-runtime` | PA | PA workflow packaging and professional task contracts | General replacement ReACT/RAG engine when native path exists |
| `packages/knowledge-engine` | PA | WeKnora adapter, evidence normalization, error and timeout contracts | PA-owned authoritative chunks, vectors, provider payloads, or secrets |
| `platform/weknora` | WeKnora fork | Native RAG, document, Wiki, AgentQA, tools, MCP, Web Search, model, parser, vector, data source | PA product history, PA business DB, or PA presentation behavior |
| `infra` | Shared delivery | Compose, images, deployment configuration, runtime wiring | Product business logic |
| `docs/evidence` | Validation | Current evidence and acceptance reports | Secrets, raw business documents, logs, or cached PASS claims |

## 7. Hard Invariants

### 7.1 Git and history

- Final state has exactly one `.git` directory at repository root.
- Inspect both current Git repositories before any file or history operation.
- Preserve all user changes and untracked product artifacts until classified.
- Create recoverable branch/tag/patch evidence before any approved nested-Git
  removal or history integration.
- Never use `git reset --hard`, destructive checkout, branch deletion,
  unapproved rebase, or unapproved history filtering.
- Do not remove a nested Git directory until `PAR-P0-01` evidence proves the
  complete nested history is reachable from the canonical repository and the
  user explicitly approves the removal.

### 7.2 Relocation discipline

- Use `git mv` for tracked relocations after the canonical baseline is clean.
- Keep pure moves separate from imports, build, behavior, or documentation
  rewrites whenever practical.
- Move one ownership boundary per task.
- Do not combine WeKnora platform relocation and PA application relocation in
  one task.
- Preserve temporary compatibility only when it is documented, tested, and
  removed by an explicit later task.
- Establish the PA Python package/workspace contract before relocating scripts
  that infer the repository root with `Path.parents` or mutate `sys.path`.
- Before creating root PA `packages/`, isolate native Docker contexts under
  `platform/weknora/` and prove every `COPY packages/` source.

### 7.3 Product and platform integrity

- PA remains the frontend/BFF/history/citation/audit product.
- WeKnora remains the native capability source.
- Native Go patches must remain attributable and testable after relocation.
- PA adapter paths must remain the only normal PA-to-WeKnora integration path.
- No task may mark a path migration complete while imports, Compose contexts,
  workflow paths, or validation scripts still silently reference old paths.

### 7.4 Data and credential safety

- Never print, move into Git, or commit `.env` values, API keys, service tokens,
  passwords, private endpoints, private keys, raw documents, uploads, DBs,
  logs, caches, raw prompts, provider payloads, or vectors.
- Runtime artifacts must end in a single ignored local-data convention such as
  `.local/`, named volumes, or external storage.
- Personal/portfolio artifacts require an explicit keep/archive/export decision;
  they must not be silently deleted.

## 8. Transitional Path Map

| Current path | Target path | Notes |
| --- | --- | --- |
| legacy PA API tree | `apps/pa-api` | Preserve FastAPI application and PA business DB behavior. |
| legacy PA Web tree | `apps/pa-web` | Becomes the only PA product frontend. |
| legacy PA Agent tree | `packages/agent-runtime` | Keep PA workflow layer separate from native Agent engine. |
| legacy PA Knowledge Engine tree | `packages/knowledge-engine` | Preserve adapter and evidence contracts. |
| outer WeKnora `internal`, `cmd`, `client`, native `frontend`, `migrations`, and related source | `platform/weknora/...` | Move as one controlled platform subtree. |
| outer `docker`, `helm`, and Compose files | `infra/*` plus a root `compose.yaml` entry | Update paths after platform relocation. |
| outer and nested PA scripts | `scripts/dev`, `scripts/ops`, `scripts/release`, `scripts/validation` | One command surface; eliminate duplicate entry points. |
| bootstrap PAR checker | `scripts/validation/check_pa_repository_reorganization.py` | Preserve `--root`, governance, final, JSON, and self-test contracts during the move. |
| PA stage specs and reports | `docs/stages`, `docs/evidence`, `docs/archive` | Keep current evidence distinct from historical reports. |
| nested repo-local Skills | root `.github/skills` | Move and update paths when the PA root becomes canonical. |
| protected legacy `resume_project` directory | explicit user-approved archive/export location | Never delete or publish by default. |

## 9. Execution Protocol

Every `PAR-*` run must:

1. Work from the current repository root.
2. Read this spec from
   `docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md`.
3. Stop if a second active copy appears with unexplained divergence.
4. Read the repo-local and `.agents` copies of
   `pa-repository-architecture-reorganization/SKILL.md`.
5. Read `docs/architecture/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md` and
   `docs/archive/wnid/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md`
   before changing ownership boundaries.
6. Run outer and nested `git status -sb`, `git log --oneline -5`, and
   `git remote -v` while both repositories exist.
7. Execute exactly one `PAR-*` task id per run.
8. Before editing, state in Chinese the task id, task class, planned paths,
   validation, expected evidence, and destructive approval boundary.
9. Preserve unrelated dirty files and do not stage them.
10. Update this spec and the task evidence report after validation.

Task classes:

- governance/audit/map;
- Git history/remote boundary;
- WeKnora platform relocation;
- PA apps/packages relocation;
- path/import/build/infra migration;
- docs/runtime hygiene;
- validation/clean-clone/handoff.

## 10. Status and Evidence States

```text
[ ] not started
[~] real partial progress; full task contract not complete
[x] complete with required evidence
[!] blocked by approval, history, path, runtime, or validation gap
[b] explicitly removed from scope by the user
```

| Evidence | Use |
| --- | --- |
| `audit/map` | Inventory, path map, Git/ref map, ownership map |
| `git-integrity` | Ref reachability, preserved changes, one-root proof |
| `static` | Import/path/reference scans and diff checks |
| `build` | Python, frontend, Go, image, or Compose build evidence |
| `live-service` | PA and WeKnora health/status evidence |
| `live-workflow` | Document, RAG, dialogue, Wiki, MCP, Web Search evidence |
| `clean-clone` | Fresh checkout setup/build/start/acceptance evidence |
| `blocked` | Exact approval, history, runtime, or path blocker |

Directory existence alone is never final PASS.

## 11. Task Board

| Task id | Priority | Title | Status | Required evidence |
| --- | --- | --- | --- | --- |
| PAR-0-01 | Governance | Reorganization spec and paired skills | [x] | This spec; repo-local and `.agents` skill mirrors; skill validation, diff check, mirror check, keyword and sensitive scans. |
| PAR-0-02 | P0 | Full repository inventory and canonical-baseline map | [x] | [Baseline map](../../evidence/PA_REPOSITORY_BASELINE_MAP_PAR_0_02.md): outer/nested refs, remotes, stash, tracked/untracked/ignored classification, exact PA tree equality, native delta, path risks, preservation gates, and candidate source recommendation. |
| PAR-0-03 | P0 | Reorganization acceptance harness | [x] | [Harness report](../../evidence/PA_REPOSITORY_REORGANIZATION_ACCEPTANCE_HARNESS_PAR_0_03.md) and `scripts/validation/check_pa_repository_reorganization.py`; governance/JSON/self-test pass, while current `--final` truthfully fails on required migration blockers. |
| PAR-P0-01 | P0 | Freeze coherent product/runtime baseline | [x] | [Freeze report](../../evidence/PA_REPOSITORY_COHERENT_BASELINE_FREEZE_PAR_P0_01.md): coherent tag at `e7b258c`, exact PA subtree equality, verified dual-repository bundles and full Git snapshots, classified dirty/local work, and isolated baseline validation. |
| PAR-P0-02 | P0 | Establish one canonical Git root | [x] | [Consolidation report](../../evidence/PA_REPOSITORY_ONE_ROOT_CONSOLIDATION_PAR_P0_02.md): all nested history/tag/stash evidence is reachable from outer archive refs; the approved nested `.git` relocation is preserved owner-only; one active root and one canonical `origin` are verified. |
| PAR-P1-01 | P1 | Relocate WeKnora under `platform/weknora` | [x] | [Relocation evidence](../../evidence/PA_REPOSITORY_WEKNORA_PLATFORM_RELOCATION_PAR_P1_01.md): 1,855 tracked renames, coherent 1,859-file native baseline, attribution/patch ledgers, Go/import/build-context validation, native/client/CLI tests, and no PA product move. |
| PAR-P1-02 | P1 | Promote PA apps and packages | [x] | [Relocation evidence](../../evidence/PA_REPOSITORY_PA_APPS_PACKAGES_RELOCATION_PAR_P1_02.md): 326 tracked moves plus 18 classified source additions place PA API/Web/Agent/Knowledge Engine at their target paths; Python imports, focused regression checks, WNID final acceptance, TypeScript/build, native Docker-context isolation, and governance gates pass without feature behavior change. |
| PAR-P2-01 | P1 | Repair imports and workspace metadata | [x] | [Workspace/import evidence](../../evidence/PA_REPOSITORY_WORKSPACE_IMPORT_REPAIR_PAR_P2_01.md): three installable Python distributions, root Python/Node workspaces, isolated wheel/import proof, backend test discovery, TypeScript/Vite aliases and build, import-shim removal, regression checks, and governance gates pass. |
| PAR-P2-02 | P1 | Consolidate Compose, Docker, Helm, and workflows | [x] | [Infrastructure evidence](../../evidence/PA_REPOSITORY_INFRASTRUCTURE_CONSOLIDATION_PAR_P2_02.md): root Compose and `infra/*` ownership, native/PA image contexts, root workflows, env examples, compatibility links, Compose/BuildKit/product regression, and governance gates pass. |
| PAR-P2-03 | P1 | Consolidate developer, ops, release, and validation commands | [x] | [Command-surface evidence](../../evidence/PA_REPOSITORY_COMMAND_SURFACE_CONSOLIDATION_PAR_P2_03.md): root Makefile plus `scripts/dev`, `scripts/ops`, `scripts/release`, and `scripts/validation`; tracked moves, caller repair, command/checker contracts, backend/Web regression, Skill, status, diff, and safety checks pass without command shims or product behavior changes. |
| PAR-P3-01 | P2 | Reorganize product, architecture, operations, evidence, and archive docs | [x] | [Documentation information-architecture evidence](../../evidence/PA_REPOSITORY_DOCUMENTATION_INFORMATION_ARCHITECTURE_PAR_P3_01.md): PA-first root README/spec/architecture, current/evidence/archive boundaries, 18 root Skills, repaired active callers and links, explicit protected-personal-material disposition, product regression, and safety gates pass. |
| PAR-P3-02 | P2 | Runtime artifact and ignore hygiene | [x] | [Runtime/ignore evidence](../../evidence/PA_REPOSITORY_RUNTIME_ARTIFACT_IGNORE_HYGIENE_PAR_P3_02.md): consolidated root policy, `.local`/volume ownership, exact runtime and legitimate-source probes, preserved legacy fallback, unchanged runtime-object counts, zero unsafe tracked artifacts, product regression, Skill, service-status, diff, and safety gates pass without reading, moving, or deleting user data. |
| PAR-P3-03 | P2 | Finalize upstream attribution and PA native patch ledger | [x] | [Attribution and patch-ledger evidence](../../evidence/PA_REPOSITORY_UPSTREAM_ATTRIBUTION_PATCH_LEDGER_PAR_P3_03.md): root license/notice boundaries, official version-tag commit, quantified reconstructed upstream anchor, local import/coherent baselines, exact 50-path controlled inventory, 35-path WNID subset, checker gates, product regression, and safety validation. |
| PAR-P4-01 | P0 | Static, unit, and build acceptance | [x] | [Static/build acceptance evidence](../../evidence/PA_REPOSITORY_STATIC_BUILD_ACCEPTANCE_PAR_P4_01.md): root static contract, PA Python/backend/Web, controlled and broad native Go tests/vet/builds, native frontend build, Compose/Docker/workflow/Helm checks, product regressions, Skill mirrors, path, diff, sensitive, Git-root, and read-only service gates. |
| PAR-P4-02 | P0 | Live PA plus WeKnora workflow acceptance | [x] | [Live workflow evidence](../../evidence/PA_REPOSITORY_LIVE_WORKFLOW_ACCEPTANCE_PAR_P4_02.md): non-mock health/status, temporary document and Wiki KBs, Quick Q&A/RAG/ReACT, MCP/Web Search, history/citation/audit, 7-route desktop/mobile product matrix, WNID dialogue browser, and zero-resource cleanup pass from root paths. |
| PAR-P4-03 | P0 | Clean-clone final acceptance and handoff | [x] | [Clean-clone handoff](../../handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md): exact-index export, real temporary clone, one Git root, fresh setup/build/Compose, isolated start/status/health, live workflow/browser reproduction, clean checkout, and final checker pass; canonical repository/version and release-owner action are named. |

## 12. Task Cards

### PAR-0-01: Reorganization spec and paired skills

- Scope: governance artifacts only.
- Editable files: this spec, repo-local skill, `.agents` skill mirror, and their
  generated `agents/openai.yaml` files.
- Forbidden: product source, Git history, branch switching, nested `.git`
  removal, path moves, runtime config, or service mutation.
- Acceptance: no initializer placeholder markers; both skills validate and match; target
  architecture, task board, safety rules, and final acceptance are explicit.

### PAR-0-02: Full repository inventory and canonical-baseline map

- Inspect outer and nested commits, refs, remotes, worktrees, ignored files,
  untracked files, native patches, PA changes, workflows, docs, and absolute
  path references.
- Identify which ref contains every current PA and WeKnora WNID change.
- Do not move files, stage changes, or select a canonical ref from inference.

### PAR-0-03: Reorganization acceptance harness

- Add a deterministic checker for governance and final states.
- Final mode must fail on nested Git, missing target directories, old canonical
  references, unsafe tracked artifacts, or incomplete evidence.
- Bootstrap path: the legacy PA backend validation tree recorded in the
  harness evidence.
- Target path: `scripts/validation/check_pa_repository_reorganization.py`.
- Preserve `--root`, `--json`, `--self-test`, and `--final` behavior when the
  checker moves.
- Final evidence file contracts:
  - `docs/evidence/PA_REPOSITORY_STATIC_BUILD_ACCEPTANCE_PAR_P4_01.md`;
  - `docs/evidence/PA_REPOSITORY_LIVE_WORKFLOW_ACCEPTANCE_PAR_P4_02.md`;
  - `docs/handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md`.

### PAR-P0-01: Freeze coherent product/runtime baseline

- Preserve both repositories and all dirty/untracked user work first.
- Materialize one coherent ref containing PA product code, WNID artifacts, and
  matching native Go patches.
- Run the pre-reorganization acceptance suite without deleting old refs.
- Evidence: `PA_REPOSITORY_COHERENT_BASELINE_FREEZE_PAR_P0_01.md` plus the
  ignored owner-only recovery set under `tmp/par-p0-01-recovery/20260714`.

### PAR-P0-02: Establish one canonical Git root

- Record exact nested-history reachability and recovery instructions.
- Assign unambiguous `origin` and optional upstream roles.
- Removing or relocating a nested `.git` requires explicit user approval after
  recoverability evidence passes.
- Current evidence: `PA_REPOSITORY_ONE_ROOT_CONSOLIDATION_PAR_P0_02.md`.
  Non-destructive history import and the explicitly approved physical one-root
  consolidation are complete.

### PAR-P1-01: Relocate WeKnora platform

- Move the full controlled native platform subtree to `platform/weknora` using
  tracked moves.
- Add upstream and PA patch ledgers.
- Repair only platform-relative references required by the move.

### PAR-P1-02: Promote PA apps and packages

- Move PA API/Web/Agent/Knowledge Engine into `apps/` and `packages/`.
- Preserve runtime contracts and module ownership.
- Defer broad infrastructure cleanup to later tasks.

### PAR-P2-01: Repair imports and workspace metadata

- Establish stable Python packaging/import roots and frontend workspace paths.
- Update test discovery and remove old nested-directory dependence.

### PAR-P2-02: Consolidate infrastructure

- Create one root `compose.yaml` product entry.
- Consolidate Docker/Helm/env/workflow files and validate every build context.

### PAR-P2-03: Consolidate command surface

- Group commands by dev, ops, release, and validation.
- Provide one obvious root entry and remove or document duplicate shims.

### PAR-P3-01: Reorganize documentation

- Keep root documentation product-first and separate current from historical
  evidence.
- Move personal materials only after the user chooses an archive destination.
- Update relative links and skill/spec paths.

### PAR-P3-02: Runtime artifact hygiene

- Classify local-only files before modifying ignore rules.
- Exclude artifacts without deleting real data or secrets.

### PAR-P3-03: Attribution and patch ledger

- Record upstream WeKnora repository/version/commit and license.
- List controlled native exception areas and PA acceptance evidence.

### PAR-P4-01: Static, unit, and build acceptance

- Run PA and native checks from the new paths.
- Require old-path scans, mirror checks, Compose config, and sensitive scans.

### PAR-P4-02: Live workflow acceptance

- Start the reorganized stack and validate real non-mock workflows.
- Preserve confirmation, audit, history, citations, MCP, and Web Search.

### PAR-P4-03: Clean-clone final acceptance

- Clone into a temporary clean directory.
- Prove one Git root, setup, build, start, status, core workflows, browser
  acceptance, and final handoff.

## 13. Validation Commands for PAR-0-01

Run from the repository root:

```bash
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py .github/skills/pa-repository-architecture-reorganization
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/pa-repository-architecture-reorganization
diff -u .github/skills/pa-repository-architecture-reorganization/SKILL.md .agents/skills/pa-repository-architecture-reorganization/SKILL.md
diff -u .github/skills/pa-repository-architecture-reorganization/agents/openai.yaml .agents/skills/pa-repository-architecture-reorganization/agents/openai.yaml
git diff --check -- docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md .github/skills/pa-repository-architecture-reorganization
rg -n "\x54ODO|\[\x54ODO" docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md .github/skills/pa-repository-architecture-reorganization .agents/skills/pa-repository-architecture-reorganization
```

The placeholder scan must return no matches. Also scan the new artifacts for private
keys, credential assignments, private endpoints, raw documents, and local data.

### PAR-0-03 checker validation

Run from the repository root:

```bash
python3 -c 'from pathlib import Path; p=Path("scripts/validation/check_pa_repository_reorganization.py"); compile(p.read_bytes(), str(p), "exec")'
python3 scripts/validation/check_pa_repository_reorganization.py --self-test
python3 scripts/validation/check_pa_repository_reorganization.py
python3 scripts/validation/check_pa_repository_reorganization.py --json
python3 scripts/validation/check_pa_repository_reorganization.py --final
```

The first four commands must pass. The current `--final` command must return
non-zero and name the remaining structural, path, artifact, and evidence gaps.
After `PAR-P4-03`, the same final command must pass from a fresh clone.

## 14. Progress Log

| Date | Task id | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 2026-07-14 | PAR-0-01 | [x] | Governance artifacts: this spec plus repo-local and `.agents` skill mirrors; validation commands in Section 13. | Establishes PA-first monorepo target, one-Git-root rule, safe migration order, explicit approval boundary for nested Git removal, task board, and clean-clone final acceptance. No product files or Git history were changed. |
| 2026-07-14 | PAR-0-02 | [x] | `PA_REPOSITORY_BASELINE_MAP_PAR_0_02.md`; exact tree hashes, ref reachability, status/ignored inventories, path scans, and artifact validation. | Identifies outer `e7b258c` as the strongest coherent content candidate because its PA subtree exactly equals nested `e3402c7` while it also contains the native WNID patch. It does not select a canonical branch. Nested history, stash, personal materials, runtime data, and current PAR artifacts remain protected. |
| 2026-07-14 | PAR-0-03 | [x] | `check_pa_repository_reorganization.py`, self-test fixtures, governance/JSON execution, expected current final-mode blockers, and `PA_REPOSITORY_REORGANIZATION_ACCEPTANCE_HARNESS_PAR_0_03.md`. | Establishes deterministic gates for one Git root, target boundaries, PA-first identity, active old-path references, unsafe tracked artifacts, Skill/Spec placement, task/progress completeness, and final evidence. No product source or Git metadata changed. |
| 2026-07-14 | PAR-P0-01 | [x] | `PA_REPOSITORY_COHERENT_BASELINE_FREEZE_PAR_P0_01.md`; protection tags, verified bundles, full Git snapshots, governance archive, isolated candidate materialization, Python/WNID/frontend/Compose/Go checks. | Freezes coherent content at outer `e7b258c`, whose PA subtree equals nested `e3402c7`; preserves nested history and stash independently; leaves both Git roots, personal materials, private/runtime data, branches, remotes, and current checkout intact. |
| 2026-07-14 | PAR-P0-02 | [x] | `PA_REPOSITORY_ONE_ROOT_CONSOLIDATION_PAR_P0_02.md`; outer `refs/archive/pa-nested/20260714/*`, post-import bundle/full Git snapshot, isolated one-root recovery proof, approved nested Git relocation, and final one-root/remote/checker validation. | All named nested refs, stash, four post-common commits, and the only dangling commit are reachable from the outer repository without merge or rewrite. After explicit approval, nested `.git` was relocated intact to owner-only recovery storage and the local-path remote was removed; only outer `.git` and canonical `origin` remain active. |
| 2026-07-14 | PAR-P1-01 | [x] | `PA_REPOSITORY_WEKNORA_PLATFORM_RELOCATION_PAR_P1_01.md`; 1,855 `git mv` renames, coherent native blob comparison, Go list/tests/vet, Compose/Docker/CI path checks, attribution ledgers, Skill/checker/diff/sensitive gates. | Moves the full controlled WeKnora platform to `platform/weknora`, restores the four additive WNID native files and complete native WNID delta, isolates Docker `packages/` context, and preserves all PA product modules and user/runtime work. Compatibility shims and later infra/scripts/docs/upstream work are explicit. |
| 2026-07-15 | PAR-P1-02 | [x] | `PA_REPOSITORY_PA_APPS_PACKAGES_RELOCATION_PAR_P1_02.md`; 344-file coherent source proof, Git rename evidence, Python compile/import/focused regression, WNID final checker, TypeScript/Vite build, Compose package-context isolation, PAR/Skill/diff/sensitive gates. | Moves PA API/Web/Agent Runtime/Knowledge Engine to `apps` and `packages`, preserves import package names and ignored private runtime state, records explicit aliases for later workspace/commands/docs tasks, and proves two legacy smoke failures reproduce before the move rather than hiding them as PASS. |
| 2026-07-15 | PAR-P2-01 | [x] | `PA_REPOSITORY_WORKSPACE_IMPORT_REPAIR_PAR_P2_01.md`; TOML/workspace assertions, three wheel builds and isolated imports, root test discovery, Python compile/regression/WNID checks, TypeScript/Vite build, old-import-path and native-context scans, PAR/Skill/diff/sensitive gates. | Establishes installable API/Agent/Knowledge distributions and root Python/Node workspaces, removes the two package-import aliases, retains only explicitly owned command/document compatibility links, and avoids Compose, command-surface, docs, runtime-data, and product-behavior changes. |
| 2026-07-15 | PAR-P2-02 | [x] | `PA_REPOSITORY_INFRASTRUCTURE_CONSOLIDATION_PAR_P2_02.md`; four Compose entry renders, seven Dockerfile BuildKit checks, context/COPY validation, five workflow parses, Helm static checks, env examples, product regression, service-status observation, and PAR/Skill/diff/sensitive gates. | Establishes root `compose.yaml` and canonical `infra/compose`, `infra/docker`, `infra/helm`, `infra/env`, and root workflow ownership; preserves six bounded compatibility links, leaves the existing user service untouched, and records host Go/Helm CLI limits for final P4 acceptance. |
| 2026-07-15 | PAR-P2-03 | [x] | `PA_REPOSITORY_COMMAND_SURFACE_CONSOLIDATION_PAR_P2_03.md`; tracked command moves, root Makefile dry-runs, shell/Python syntax, relocated checker contracts, Compose/workflow/LaunchAgent path checks, backend/WNID/Web regression, Skill mirrors, read-only service status, diff, and sensitive gates. | Establishes one PA-first root command surface across `scripts/dev`, `scripts/ops`, `scripts/release`, and `scripts/validation`; removes three obsolete command aliases after callers migrate, preserves internal component scripts and historical P3 documentation references, and does not mutate product behavior or existing services. |
| 2026-07-15 | PAR-P3-01 | [x] | `PA_REPOSITORY_DOCUMENTATION_INFORMATION_ARCHITECTURE_PAR_P3_01.md`; classified documentation inventory, tracked moves, root identity documents, current/evidence/archive indexes, link resolution, 18 Skill validations, five mirror checks, active-path repairs, product regression, read-only service status, diff, and sensitive gates. | Makes PA AI Workbench the documentation root, moves completed stage records to explicit archives, removes the obsolete `apps/docs` link after caller migration, keeps protected personal material unread and in place pending a user-selected destination, and defers runtime hygiene, attribution finalization, and P4 acceptance. |
| 2026-07-15 | PAR-P3-02 | [x] | `PA_REPOSITORY_RUNTIME_ARTIFACT_IGNORE_HYGIENE_PAR_P3_02.md`; metadata-only runtime inventory, root and native ignore probes, preserved-object counts, local-runtime selection, checker self-test, shell/Python/backend/Web/Compose regressions, WNID/WNFC/WNX checks, Skill mirrors, read-only service status, diff, and sensitive gates. | Establishes `.local/pa-api` and `.local/pa-dev` for new checkouts, preserves current legacy runtime through path-only compatibility markers, replaces overbroad build/output ignores with explicit artifact paths, precisely ignores protected personal material, and removes no user/runtime data. |
| 2026-07-15 | PAR-P3-03 | [x] | `PA_REPOSITORY_UPSTREAM_ATTRIBUTION_PATCH_LEDGER_PAR_P3_03.md`; official ref fetch and 358-candidate Git-object comparison, root license/notices, reconstructed anchor, 50/35-path ledger equality, checker self-test/governance/JSON/root contracts, root/product regression, Skill mirrors, service-status, diff, and safety gates. | Records official `v0.6.0` tag commit separately from the non-identical import, identifies `482686d...` as a quantified reconstructed anchor rather than inventing tree equality, removes the obsolete nested notice after supersession, and leaves Go/Helm/build plus live/clean-clone proof for P4. |
| 2026-07-15 | PAR-P4-01 | [x] | `PA_REPOSITORY_STATIC_BUILD_ACCEPTANCE_PAR_P4_01.md`; root 7-test static contract, `make validate`, three Python wheels/imports, backend and PA Web checks, controlled and 78/81 broad native Go tests, server/client/CLI builds and vet, native frontend production build, Compose/Docker/workflow/Helm checks, product checker regressions, Skill mirrors, path/diff/sensitive/Git/service gates. | Completes static, unit, and build acceptance without touching the running service; records three unfiltered native Go external/upstream residual domains instead of claiming a false full-suite PASS, and leaves live workflow and clean-clone proof for P4-02/P4-03. |
| 2026-07-15 | PAR-P4-02 | [x] | `PA_REPOSITORY_LIVE_WORKFLOW_ACCEPTANCE_PAR_P4_02.md`; root `make validate-live-acceptance`, non-mock health/native status, temporary document/Wiki KBs, Quick Q&A/RAG/ReACT, suggested questions, MCP/Web Search, history/citation/audit, 7-route desktop/mobile and WNID dialogue browser matrices, secret/layout checks, and zero-resource cleanup. | Completes live acceptance without stopping or rebuilding the existing Compose project; repairs stale validation paths, preserves the configured 60-second timeout, restores MCP approval state when changed, cleans all temporary external resources, and leaves only clean-clone final acceptance/handoff for P4-03. |
| 2026-07-15 | PAR-P4-03 | [x] | `PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md`; root `make validate-clean-clone`, exact-index export, temporary seed commit and real clone, one-root/tree/cleanliness proof, fresh setup/build/Compose, isolated start/status/health, live workflow/browser reproduction, and fresh-clone final checker. | Completes PAR without changing source history or the existing WeKnora lifecycle, fixes root environment initialization for documented start, excludes the three unstaged/untracked user paths from the candidate, removes temporary clone/runtime evidence after success, and hands the staged candidate to explicit release-owner review/publication. |

## 15. Completion Criteria

The PAR stage is complete only when:

- the repository and local folder present PA AI Workbench as the root product;
- exactly one Git root exists;
- PA apps/packages and WeKnora platform ownership are explicit;
- all tracked source, refs, and approved artifacts are preserved;
- old canonical paths are removed or documented compatibility shims;
- static, unit, build, Compose, live workflow, and browser checks pass;
- a fresh clone reproduces the validated result;
- final documentation identifies the canonical repository, version, start
  command, validation command, and remaining backlog.

PAR is complete. The next release task is repository-owner release-candidate
review and publication: review the staged candidate, choose the release/version
policy, explicitly commit and push, and run remote CI/release gates. Those
actions are outside PAR and require separate authorization.
