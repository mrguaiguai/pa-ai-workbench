# PAR-P2-01 Workspace and Import Repair Evidence

- Date: 2026-07-15
- Task: `PAR-P2-01`
- Status: `[x]` validated complete
- Evidence type: path/import/build governance plus offline product regression

## 1. Scope and safety boundary

This task establishes installable Python package roots, root-level test
discovery, and a frontend workspace after `PAR-P1-02`. It does not relocate or
redesign Compose, Docker, Helm, workflows, developer commands, validation
commands, documentation, runtime data, or product behavior.

Pre-change safety evidence remained unchanged:

- branch `main`, HEAD `5549670`, and the canonical GitHub `origin` were
  retained;
- exactly one active Git root exists at the repository root;
- the mixed tracked/untracked worktree was treated as protected user work;
- no reset, checkout, rebase, history rewrite, commit, push, merge, branch
  deletion, dependency installation, or runtime-data migration was performed;
- dotenv loading was disabled for validation with `PA_SKIP_DOTENV=1`; no
  credential, database, upload, log, output, vector, cache, or personal file
  was read or moved;
- `docs/resume_project` and the preserved nested-Git recovery evidence were
  not changed.

## 2. Before-state findings

The promoted PA sources had no root Python workspace, no project metadata in
the API/Agent/Knowledge package roots, no root Node workspace, and no root
backend test-discovery contract. The API path helper resolved
`Path.parents[2]` to `apps` rather than the repository root. Two transitional
import links made `agent` and `knowledge_engine` appear below `apps`:

```text
apps/agent            -> packages/agent-runtime/agent
apps/knowledge_engine -> packages/knowledge-engine/knowledge_engine
```

The remaining `apps/backend`, `apps/frontend`, `apps/scripts`, and `apps/docs`
links support historical command/document paths. Their replacement is
explicitly assigned to `PAR-P2-03` and `PAR-P3-01`, so this task did not remove
or broadly rewrite them.

## 3. Implemented workspace contract

### Python

- root `pyproject.toml` declares a virtual `uv` workspace for the API, Agent
  Runtime, and Knowledge Engine and configures `tests/backend` discovery;
- `apps/pa-api/pyproject.toml` builds distribution
  `pa-ai-workbench-api` and declares both PA package dependencies;
- `packages/agent-runtime/pyproject.toml` builds `pa-agent-runtime`, depends on
  `pa-knowledge-engine`, and includes all three built-in Skill documents;
- `packages/knowledge-engine/pyproject.toml` builds
  `pa-knowledge-engine` with its direct runtime dependencies;
- `apps/pa-api/app/pathing.py` now exposes the real repository, app, package,
  native-platform, bootstrap-command, and bootstrap-document boundaries
  without mutating `sys.path`;
- `tests/backend/test_workspace_imports.py` validates canonical package
  discovery, repository boundaries, and built-in Skill source completeness;
- the two temporary Python import links were removed after isolated wheel
  installation and canonical-path regression succeeded.

### Frontend

- root `package.json` declares `apps/pa-web` as the Node workspace;
- `apps/pa-web/tsconfig.json` declares stable `@/* -> src/*` paths;
- `apps/pa-web/vite.config.ts` maps the same `@` alias for production builds.

`apps/COMPATIBILITY.md` now separates completed P2-01 import-shim removal from
the four command/document shims deliberately retained for later tasks.

## 4. Validation evidence

### Metadata, package, import, and test discovery

| Check | Result |
| --- | --- |
| Parse all four Python TOML files with `tomllib` | PASS |
| Root `unittest discover -s tests/backend -v` | PASS, 3/3 |
| Compile API application and scripts, Agent Runtime, Knowledge Engine, and backend tests | PASS |
| Build three wheels from sanitized temporary source copies using PEP 517/setuptools | PASS |
| Install all three wheels with `--no-deps` into an isolated temporary target | PASS |
| Import `app`, `agent`, and `knowledge_engine` from the isolated installation | PASS |
| Agent built-in Markdown resources in wheel | PASS, 3/3 |
| Canonical source import with no `apps/agent` or `apps/knowledge_engine` link | PASS |

Temporary wheel hashes identify the validated artifacts without adding build
output to the repository. The build fixed `SOURCE_DATE_EPOCH=315532800` so the
archive timestamps do not make this evidence vary between runs:

```text
pa_agent_runtime-0.1.0-py3-none-any.whl
  37257c6344e048fdbf83ab26c892cd4ab82868dcad07fc920c6c5ab9eb922ceb
pa_ai_workbench_api-0.1.0-py3-none-any.whl
  f5a820c3186dc52f6eb20efe62ed9b4c385e32fe08e177d3a6d5e75d75fda9b8
pa_knowledge_engine-0.1.0-py3-none-any.whl
  998ba8e4e36ae98d71741937716b9dffcdb90f9a22b3b8bf856c7ab5992f8262
```

The preserved application virtual environment does not include `pytest`, so
no false pytest PASS is claimed. Standard-library discovery executed the new
tests, while root `pyproject.toml` establishes the same `tests/backend` and
canonical import roots for pytest-capable clean environments.

### Product regression and frontend build

All Python checks used canonical `PYTHONPATH` entries for `apps/pa-api`,
`packages/agent-runtime`, and `packages/knowledge-engine` after the two import
links were absent.

| Check | Result |
| --- | --- |
| Load `app.main:app` with in-memory database, temporary upload path, and dotenv disabled | PASS |
| `smoke_wiki_l5.py` | PASS |
| `smoke_agent_evidence_policy_m2.py` | PASS |
| `smoke_rag_debug_params_m2.py` | PASS |
| WNID final acceptance | PASS, 17/17 complete and final ready |
| TypeScript `tsc --noEmit` | PASS |
| Vite production build | PASS, 1,589 modules transformed |
| Root Node workspace metadata assertion | PASS |

### Path, native-context, and governance checks

| Check | Result |
| --- | --- |
| `apps/agent` and `apps/knowledge_engine` absence | PASS |
| Active API/package/test scan for those import-shim paths | PASS, zero matches |
| Go scan for PA app/package imports | PASS, zero matches |
| Native Compose context inspection | PASS; native app/docreader contexts remain `platform/weknora` |
| `Dockerfile.docreader` `COPY packages/` collision guard | PASS; the build context remains the native platform |
| PAR checker self-test | PASS |
| PAR checker governance and JSON modes | PASS; one Git root, governance ready |
| PAR checker `--final` | Expected FAIL with later-task blockers only |
| Both PAR Skill copies | PASS |
| Skill and `agents/openai.yaml` mirror comparison | PASS |
| Staged and unstaged `git diff --check` | PASS |
| Sensitive-value and protected-path scans | PASS |

After this task, the expected final-checker blocker codes remain:

```text
canonical_skill_missing
canonical_spec_missing
incomplete_progress_evidence
incomplete_task_board
legacy_product_tree_present
missing_final_evidence
missing_target_boundaries
root_product_identity
stale_skill_path
```

None is a P2-01 import/workspace error. They belong to later infrastructure,
command, documentation, hygiene, final-evidence, and handoff tasks.

## 5. Compatibility shims and residual risk

The following tracked relative links remain intentional and versioned:

```text
apps/backend  -> apps/pa-api
apps/frontend -> apps/pa-web
apps/scripts  -> pa-ai-workbench/scripts
apps/docs     -> pa-ai-workbench/docs
```

The first three are owned by `PAR-P2-03`; the docs link is owned by
`PAR-P3-01`. Historical validation scripts still compute `apps` as their
working root and therefore must not lose these links until their command paths
are migrated. Two ignored local-only dependency links (`apps/pa-api/.venv` and
`apps/pa-web/node_modules`) also remain; clean environments install declared
dependencies normally. The API's ignored legacy runtime-data selection remains
owned by `PAR-P3-02`.

The next task is `PAR-P2-02`: consolidate Compose, Docker, Helm, and workflows
without combining the later command or documentation migrations.
