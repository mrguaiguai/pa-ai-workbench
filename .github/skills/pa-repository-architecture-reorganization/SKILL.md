---
name: pa-repository-architecture-reorganization
description: Use this skill for PA AI Workbench PAR-* repository architecture reorganization work, including Git consolidation, PA-first monorepo ownership, controlled WeKnora placement, apps/packages/infra/scripts/docs migration, preserved user work, and clean-clone acceptance without product regressions.
---

# PA Repository Architecture Reorganization

Use this skill for every `PAR-*` task. Treat repository reorganization as a
high-risk migration: preserve history and user work first, move one ownership
boundary at a time, and validate behavior after paths change.

Default working directory: the current repository root.

## Source of Truth

At the start of each task:

1. Read `docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md`.
2. Stop if a second active Spec copy appears with unexplained divergence.
3. Read `docs/architecture/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md` and
   `docs/archive/wnid/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md`
   before changing module ownership.
4. Read the repo-local and outer `.agents` copies of this skill. Obey the
   stricter rule and repair divergence in a governance task.
5. If an unexpected nested Git root exists, run these in both repositories:
   - `git status -sb`;
   - `git log --oneline -5`;
   - `git remote -v`.

## Task Binding

- Execute exactly one `PAR-*` task id per run.
- If the user names a task id, use it.
- If the user says continue, choose the earliest unfinished task in this order:
  `PAR-0-02`, `PAR-0-03`, `PAR-P0-01`, `PAR-P0-02`, `PAR-P1-01`,
  `PAR-P1-02`, `PAR-P2-01`, `PAR-P2-02`, `PAR-P2-03`, `PAR-P3-01`,
  `PAR-P3-02`, `PAR-P3-03`, `PAR-P4-01`, `PAR-P4-02`, `PAR-P4-03`.
- Do not silently combine Git consolidation, WeKnora relocation, PA relocation,
  infrastructure migration, and documentation cleanup.
- Update task status only after required evidence passes or a truthful blocker
  is recorded.

## Classify Before Editing

Before modifying files, state in Chinese:

1. Task id.
2. Task class:
   - governance/audit/map;
   - Git history/remote boundary;
   - WeKnora platform relocation;
   - PA apps/packages relocation;
   - path/import/build/infra migration;
   - docs/runtime hygiene;
   - validation/clean-clone/handoff.
3. Planned files or paths.
4. Validation method.
5. Expected evidence type.
6. Any destructive approval boundary.

## Git and User-Work Safety

- Treat the outer and nested repositories as independent sources until
  `PAR-P0-02` is complete.
- Preserve unrelated modified, untracked, ignored, and runtime files.
- Never use `git reset --hard`, destructive checkout, unapproved rebase,
  history filtering, branch deletion, or broad cleanup.
- Do not remove or relocate a `.git` directory without explicit user approval
  after ref reachability, backup, and recovery evidence passes.
- Do not assume the visible filesystem equals one coherent commit. Prove which
  refs contain current PA code and matching native patches.
- Use explicit paths for staging. Do not stage `.env`, DBs, uploads, logs,
  caches, output, tmp, `node_modules`, build artifacts, or personal materials.
- Do not commit, push, merge, or rewrite history unless the user explicitly
  requests that action.

## Structural Rules

- Final repository has one Git root and PA AI Workbench as the root product.
- Place the controlled WeKnora source under `platform/weknora/` with upstream
  and PA patch attribution.
- Place PA API/Web under `apps/` and PA Agent/Knowledge Engine under
  `packages/`.
- Keep PA as product shell/BFF/history/citation/audit and WeKnora as the native
  RAG/Wiki/Agent/MCP/Web Search/model/parser/vector/connector platform.
- Use `git mv` for tracked relocations after the baseline is coherent.
- Keep pure moves separate from behavior changes. Make only the minimum path,
  import, build, or configuration changes required to validate the move.
- Move one ownership boundary per task.
- Document every temporary compatibility shim and remove it in an explicit
  later task.
- Never mark a move complete while canonical scripts, workflows, imports,
  Compose contexts, docs, or skills still silently depend on the old path.

## Path and Documentation Migration

- Use `rg` before edits to inventory absolute paths, legacy bootstrap paths,
  references, build contexts, Python path injection, frontend API paths, skill
  locations, and report links.
- Keep the root README and product spec PA-first.
- Separate product, architecture, operations, stages, current evidence, and
  historical evidence.
- Do not delete the protected legacy `resume_project` directory or other
  personal materials. Move or export them only after the user selects a
  destination.
- Keep the root repo-local Skill and `.agents` mirror synchronized.

## Validation

- Governance tasks require skill validation, mirror comparison,
  `git diff --check`, path/keyword checks, and sensitive scans.
- Git tasks require ref reachability, preserved-change inventory, recovery
  instructions, and one-root evidence.
- PA relocation requires Python import/compile/tests and frontend build/tests.
- WeKnora relocation requires focused or broader native Go tests and build-path
  validation.
- Infrastructure tasks require `docker compose config`, image/build-context,
  workflow, env-example, and service-status checks.
- Final acceptance requires live PA/WeKnora workflows and a fresh temporary
  clone proving one Git root, setup, build, start, health, browser, history,
  citation, audit, MCP, and Web Search contracts.
- Keep audit, static, build, live-service, live-workflow, clean-clone, and
  blocked evidence distinct.

## Progress Updates

When evidence changes, update in the same task:

1. The task row in the PAR spec.
2. The PAR progress log.
3. The task evidence report under the current documentation layout.
4. Any acceptance checker, path map, architecture map, or handoff report
   affected by the change.

Use only:

```text
[x] validated complete
[~] real partial progress
[!] blocked by approval, history, path, runtime, or validation gap
[b] explicitly removed by the user
```

## Final Output

End each task with changed or moved paths, validation results, evidence type,
preserved user-work notes, approval or blocker details, compatibility shims,
risks, and the next `PAR-*` task id.
