# PAR-0-03 Repository Reorganization Acceptance Harness

> Date: 2026-07-14
>
> Task: `PAR-0-03`
>
> Decision: `PASS`
>
> Evidence type: `checker_execution + static + expected-final-blockers`

## 1. Purpose

This task adds a deterministic repository-level acceptance checker before any
branch freeze, nested-Git consolidation, or source relocation.

Bootstrap checker path:

```text
backend/scripts/check_pa_repository_reorganization.py
```

Current full path:

```text
pa-ai-workbench/backend/scripts/check_pa_repository_reorganization.py
```

Target path after command-surface reorganization:

```text
scripts/validation/check_pa_repository_reorganization.py
```

The checker discovers either the bootstrap Spec or the final canonical Spec.
It also accepts `--root`, so a fresh clone or temporary worktree can be checked
without depending on the current folder name.

## 2. Modes

### Governance mode

Default mode validates the current transition contract without pretending the
repository is already reorganized.

It requires:

- the PAR Spec;
- the PAR-0-02 baseline report;
- this PAR-0-03 harness report;
- the repo-local reorganization Skill;
- Skill mirror equality when the local `.agents` mirror exists;
- all 16 PAR task rows;
- `PAR-0-01`, `PAR-0-02`, and `PAR-0-03` marked `[x]`;
- baseline preservation markers for the coherent candidate, nested history,
  stash, and exact PA tree equality;
- no secret-shaped text in governance artifacts.

Governance mode may pass while reporting `final_ready=false`. That result means
the planning and guardrail contract is valid, not that the repository migration
is complete.

### Final mode

`--final` turns every final-state gap into a blocking failure.

It enforces:

- exactly one root Git repository and no nested `.git` entry;
- no remaining `pa-ai-workbench` legacy product tree;
- all PA-first target directories and root product files;
- canonical Spec and repo-local Skill paths;
- PA AI Workbench root README identity;
- all 16 task rows and progress rows complete;
- required static/build, live-workflow, and clean-clone evidence files;
- no unsafe tracked runtime, build, secret, personal, or cache artifacts;
- no stale absolute bootstrap path in the active Skill;
- no old canonical path in active product, architecture, operations, scripts,
  tests, root configuration, or handoff files.

Final evidence paths are:

```text
docs/evidence/PA_REPOSITORY_STATIC_BUILD_ACCEPTANCE_PAR_P4_01.md
docs/evidence/PA_REPOSITORY_LIVE_WORKFLOW_ACCEPTANCE_PAR_P4_02.md
docs/handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md
```

## 3. Commands

Run from the current PA project directory:

```bash
python3 backend/scripts/check_pa_repository_reorganization.py
python3 backend/scripts/check_pa_repository_reorganization.py --json
python3 backend/scripts/check_pa_repository_reorganization.py --final
python3 backend/scripts/check_pa_repository_reorganization.py --self-test
```

Run from an arbitrary checkout:

```bash
python3 backend/scripts/check_pa_repository_reorganization.py --root /path/to/repository
```

After the checker moves to its final path, use the same flags with
`scripts/validation/check_pa_repository_reorganization.py`.

## 4. Safety Model

The checker may read:

- governance Markdown and Skill text;
- directory and file existence;
- Git-tracked path names;
- active text files used for path migration checks.

It does not read:

- environment values;
- databases;
- upload contents;
- logs;
- output bodies;
- temporary PDFs;
- credentials or provider payloads.

Large runtime and dependency directories are pruned during traversal. Output is
bounded to safe path names and redacted exception summaries.

The checker never fetches, checks out, stages, commits, changes a remote,
starts a service, deletes a file, or modifies Git metadata.

## 5. Self-Test Contract

`--self-test` creates temporary synthetic fixtures outside the repository.

The positive fixture contains:

- one root Git marker;
- all final target boundaries;
- canonical Spec and Skill locations;
- a PA-first root README;
- all PAR task and progress rows complete;
- all three final evidence files;
- no old canonical references or unsafe artifacts.

The negative fixture independently proves rejection of:

| Required gate | Checker code |
| --- | --- |
| Nested Git | `nested_git` |
| Missing target directories/files | `missing_target_boundaries` |
| Unsafe tracked/local fixture artifact | `unsafe_tracked_artifact` |
| Old canonical path | `old_canonical_reference` |
| Stale Skill path | `stale_skill_path` |
| Incomplete task board | `incomplete_task_board` |
| Incomplete progress evidence | `incomplete_progress_evidence` |
| Missing final evidence | `missing_final_evidence` |

Actual self-test result:

```text
PA repository reorganization checker self-test passed
- positive_final_fixture: passed
- negative_required_gates: passed
```

## 6. Current Governance-Mode Evidence

Expected result after this task is marked complete:

```text
PA repository reorganization acceptance check passed
- evidence_type: checker_execution
- mode: governance
- governance_ready: true
- final_ready: false
- task_rows: 16
- completed_tasks: 3
- progress_rows: 3
- git_roots: 2
- final_blockers: 12
- final_blocker_codes: canonical_skill_missing, canonical_spec_missing, incomplete_progress_evidence, incomplete_task_board, legacy_product_tree_present, missing_final_evidence, missing_target_boundaries, nested_git, old_canonical_reference, root_product_identity, stale_skill_path, unsafe_tracked_artifact
```

The final blockers remain informational in governance mode.

## 7. Current Final-Mode Evidence

Final mode must fail on the current checkout. The expected blocking categories
include:

```text
canonical_skill_missing
canonical_spec_missing
incomplete_progress_evidence
incomplete_task_board
legacy_product_tree_present
missing_final_evidence
missing_target_boundaries
nested_git
old_canonical_reference
root_product_identity
stale_skill_path
unsafe_tracked_artifact
```

This is a truthful expected failure. It proves the checker does not convert the
presence of planning documents into repository-completion PASS.

## 8. JSON Contract

`--json` emits:

- summary;
- governance issues;
- final issues;
- blocking issues for the selected mode.

The summary includes mode, governance/final readiness, task and progress row
counts, Git-root count, final blocker count, and stable blocker codes. This is
the integration surface for later CI and clean-clone checks.

## 9. Validation Performed

| Check | Result |
| --- | --- |
| Python bytecode compilation | PASS |
| Positive final fixture | PASS |
| Negative required-gate fixture | PASS |
| Governance mode on current checkout | PASS |
| JSON mode on current checkout | PASS |
| Final mode on current checkout | Expected non-zero with required blocker codes |
| Skill validation and mirror comparison | PASS |
| Spec/report/checker whitespace checks | PASS |
| Placeholder and sensitive-assignment scans | PASS |

No product behavior, Git history, branch, remote, service, private runtime data,
or personal material was changed.

## 10. Decision

`PAR-0-03` is complete when the checked-in artifacts retain the validated
results above. The checker is now the static guardrail for every later PAR task.

The next task is `PAR-P0-01`: preserve both histories and hidden refs, then
freeze a coherent PA plus native WNID baseline without changing the current
hybrid worktree destructively.
