# PAR-P1-02 PA Apps and Packages Relocation

> Date: 2026-07-15
>
> Task: `PAR-P1-02`
>
> Decision: `PASS`
>
> Evidence type: `git-integrity + static + build`

## 1. Result

The four PA product ownership boundaries now live at their target paths:

| PA boundary | Previous path | Canonical path | Source files |
| --- | --- | --- | ---: |
| FastAPI BFF | `pa-ai-workbench/backend` | `apps/pa-api` | 214 |
| React product shell | `pa-ai-workbench/frontend` | `apps/pa-web` | 27 |
| Agent Runtime import package | `pa-ai-workbench/agent` | `packages/agent-runtime/agent` | 48 |
| Knowledge Engine import package | `pa-ai-workbench/knowledge_engine` | `packages/knowledge-engine/knowledge_engine` | 55 |

The 344-file source set consists of the complete 343-file coherent baseline
for these boundaries plus the later PAR acceptance checker. Python imports
remain `agent` and `knowledge_engine`; no feature behavior, native WeKnora Go
ownership, Compose topology, CI workflow, or documentation hierarchy was
redesigned in this task.

## 2. Pre-Move Safety and Recovery

Before moving files, the physical source was compared against
`par-p0-01-coherent-baseline-20260714`:

```text
baseline_checked=343
blob_mismatch=0
scope_untracked=18
```

The 18 untracked source files were classified as 16 WNID backend scripts, the
WNID Dialogue page, and the later PAR checker. No arbitrary untracked file was
included.

An owner-only recovery set was created at the ignored path:

```text
tmp/par-p1-02-recovery/20260715
```

| Artifact | SHA-256 | Purpose |
| --- | --- | --- |
| `index-before-pa-relocation` | `ec1cdee0fecb8b3d3d8a44ad2ad6a7fae6e2fa42b26e62fe0574d7adde096aa0` | Exact pre-move Git index, including the completed PAR-P1-01 staging state |
| `pa-source-before-relocation.tar.gz` | `ff3686d7e353864e3ed5ef60c669868a13ecce2464b82b5beb9d765ff87b3052` | The explicit 344-file PA source set only |

Both artifacts are mode `0600`; the directory is mode `0700`. The archive
does not include `.env`, `.venv`, databases, uploads, logs, output, dependency
caches, build output, or personal materials.

## 3. Git Move Evidence

The task used `git mv` for all 326 paths tracked by the active outer index and
moved the 18 classified source additions to their mapped target paths. After
the move and before path repair, all 343 coherent-baseline blobs still matched
their mapped targets exactly.

Staged rename detection for this task reports:

```text
find-renames=50%: 323 renames; 3 delete/add pairs with large content deltas
find-renames=1%:  326 renames; 25 additions; 0 deletions
```

The three low-similarity files are WNID-era or move-required content deltas;
all were moved with `git mv`. The 25 additions are exactly:

- 17 coherent-baseline WNID files that were untracked by outer `main`;
- 1 PAR checker created after the coherent baseline;
- 1 compatibility ledger and 6 explicit compatibility symlinks.

The old source roots contain zero indexed product files. They remain present
on disk only because ignored local `.env`, `.venv`, `node_modules`, `dist`,
database, upload, and Python-cache state was deliberately left in place and
was not inspected or moved.

## 4. Completeness and Intentional Deltas

The post-repair comparison checked all 343 coherent-baseline paths:

```text
baseline_checked=343
intentional_blob_delta=3
mode_mismatch=0
```

Only these move-required runtime-path files differ from the coherent source
blobs:

- `apps/pa-api/app/config.py`;
- `apps/pa-api/app/database.py`;
- `apps/pa-api/app/storage/file_store.py`.

They keep private backend runtime state at its ignored pre-move location when
that location exists, while clean clones default to `apps/pa-api`. Validation
uses `PA_SKIP_DOTENV=1`, so no local environment file is read. Database and
upload relative paths use the explicit runtime directory instead of silently
creating a second data store under the new source directory.

Direct launcher repairs were limited to:

- `pa-ai-workbench/scripts/pa-dev-services.sh`;
- `pa-ai-workbench/scripts/install-pa-launchagents.sh`;
- `platform/weknora/scripts/pa-workbench-setup.sh`;
- `platform/weknora/scripts/pa-workbench-start.sh`.

They load API source from `apps/pa-api`, frontend source from `apps/pa-web`,
and add the two package distribution roots to `PYTHONPATH`. Broader command
consolidation remains assigned to `PAR-P2-03`.

## 5. Transitional Compatibility Contract

`apps/COMPATIBILITY.md` records six relative, versioned aliases:

```text
apps/backend           -> apps/pa-api
apps/frontend          -> apps/pa-web
apps/agent             -> packages/agent-runtime/agent
apps/knowledge_engine  -> packages/knowledge-engine/knowledge_engine
apps/docs              -> bootstrap documentation tree
apps/scripts           -> bootstrap PA command tree
```

These aliases preserve the existing `Path.parents`, `sys.path`, fixture,
documentation, and validation-script assumptions without duplicating source.
They are explicit temporary shims, not canonical product paths.

The active checkout also has two ignored, local-only links that reuse existing
dependency installations without moving them:

```text
apps/pa-api/.venv
apps/pa-web/node_modules
```

They are excluded by the root ignore shim and are not tracked. Clean clones
must install dependencies normally. `PAR-P2-01` owns Python distribution
metadata and stable path discovery; `PAR-P2-03` owns command relocation;
`PAR-P3-01` owns documentation relocation; `PAR-P3-02` owns the final local
runtime-data convention.

The PAR checker intentionally skips its own bootstrap-path constants during
old-canonical-reference scanning. It continues to detect those markers in all
other active files and will lose that exception when the checker and Spec move
to their final paths.

## 6. Validation Evidence

### Python and PA contracts

| Check | Result |
| --- | --- |
| Compile all API application, API validation scripts, Agent Runtime, and Knowledge Engine Python files | PASS |
| Import `app`, `agent`, and `knowledge_engine` from the new roots | PASS |
| Load `app.main:app` with in-memory DB and dotenv disabled | PASS |
| Backend source/runtime path assertions | PASS; source is `apps/pa-api`, preserved local runtime is the ignored legacy backend directory |
| Shell syntax for PA dev/LaunchAgent and platform setup/start/check scripts | PASS |
| `smoke_wiki_l5.py` | PASS |
| `smoke_agent_evidence_policy_m2.py` | PASS |
| `smoke_rag_debug_params_m2.py` | PASS |
| `smoke_weknora_native_client_contract.py` | PASS in approved localhost-only fixture context |
| `smoke_weknora_adapter_errors_m2.py` | PASS in approved localhost-only fixture context |
| WNID final acceptance | PASS; 17/17 complete, final ready |

Two additional legacy diagnostics are not counted as relocation PASS:

- `smoke_backend_l3.py` expects an older `StatusResponse` without the required
  `weknora` field;
- `smoke_agent_l4.py` expects at least one citation for a current workflow that
  now returns zero under that old fixture.

Both failures were reproduced unchanged by extracting the pre-move 344-file
recovery archive into `/private/tmp` and running the original directory
layout. They are therefore pre-existing stale-smoke debt, not a relocation
regression. Product behavior was not changed to force those old assertions to
pass.

### Frontend

| Check | Result |
| --- | --- |
| TypeScript `tsc --noEmit` | PASS |
| Vite production build | PASS; 1,589 modules transformed |
| Package test command | Not present in `package.json`; no fake test PASS claimed |

### Native build boundary

| Check | Result |
| --- | --- |
| Go source scan for PA app/package path imports | PASS; no matches |
| Compose config with example interpolation and service env resolution disabled | PASS |
| Native app/docreader contexts | Both resolve to `platform/weknora` |
| Native frontend context | Resolves to `platform/weknora/frontend` |
| `Dockerfile.docreader` `COPY packages/` source | Still scoped to the native platform context; root PA packages cannot be copied |

No Go source changed in this task, so the focused Go test evidence from
`PAR-P1-01` remains the native behavioral evidence. This task added the
cross-boundary Go scan and Docker-context proof required by the new root
`packages` directories.

### Governance and repository safety

| Check | Result |
| --- | --- |
| PAR checker self-test | PASS |
| PAR governance and JSON modes | PASS; one Git root, governance ready |
| PAR final mode | Expected FAIL with nine later-task blocker classes |
| Task-specific target error | Resolved; missing target boundaries no longer list PA API/Web/Agent/Knowledge Engine |
| Skill validation for repo-local and `.agents` copies | PASS |
| Skill and generated metadata mirror comparison | PASS |
| Compatibility symlink target checks | PASS |
| `git diff --check` for staged and unstaged changes | PASS |
| Protected-path staging scan | PASS |
| Exact private-key/cloud-token/bearer-key scan | PASS; no matches |
| Broad credential-assignment candidate review | PASS; schema fields, redaction regexes, and safe value forwarding only |

Current PAR final blockers are expected later-stage work only:

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

## 7. Preserved User Work

- The 21 PA files that appeared modified against outer `main` were moved with
  their coherent WNID content; none was overwritten.
- Thirty-eight remaining file-level untracked items stay outside this task.
- All 13 `docs/resume_project` files remain untracked and untouched.
- Existing `.env`, password marker, database, uploads, logs, output, temporary
  files, dependencies, caches, and vectors were neither read nor moved.
- The PAR-P0 recovery sets, imported archive refs, coherent tag, GitHub
  `origin`, current branch, and HEAD were not changed.
- No commit, push, merge, branch switch, fetch, or history rewrite occurred.

## 8. Decision and Next Task

`PAR-P1-02` is complete. PA API/Web/Agent Runtime/Knowledge Engine ownership is
now explicit at the target paths, imports and frontend build pass from the new
layout, the coherent source set is complete, and private/runtime state remains
recoverable and untouched.

The next task is `PAR-P2-01`: replace transitional Python/path aliases with
installable workspace metadata, stable import roots, TypeScript/test discovery,
and a complete active old-path scan. It must not silently absorb the later
Compose, command-surface, or documentation consolidation tasks.
