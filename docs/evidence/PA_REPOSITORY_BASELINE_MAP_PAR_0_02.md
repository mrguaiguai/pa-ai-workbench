# PAR-0-02 Repository Inventory and Canonical Baseline Map

> Date: 2026-07-14
>
> Task: `PAR-0-02`
>
> Decision: `PASS` for read-only `audit/map` evidence
>
> Evidence type: `audit/map + git-integrity + static`
>
> Scope: `/Users/mac/Downloads/WeKnora-main` and its nested
> `pa-ai-workbench` Git repository

## 1. Executive Result

The current physical checkout is not one coherent commit. It combines:

```text
outer WeKnora/native files = outer main 5549670
nested PA files            = nested weknora-first-mvp e3402c7
```

The strongest existing coherent **content candidate** is the outer ref:

```text
codex/weknora-agent-learning-skill
e7b258c61d56bd44ce477ef29cf761d8ab07cdfc
```

Two independent facts prove this:

1. Its `pa-ai-workbench` subtree is object-for-object identical to the complete
   nested `e3402c7` tree.
2. The same outer commit also contains the 17 root/native WNID changes that are
   absent from the currently checked-out outer `main` worktree.

This report does **not** select, check out, merge, or rename a canonical branch.
It records `e7b258c` as the recommended content input for `PAR-P0-01`.

The nested `.git` must remain intact. The outer object database does not contain
the last four nested PA commits, and the nested repository also has an
independent stash. Content equality is not history preservation.

## 2. Read-Only Scope and Safety Boundary

This task performed no fetch, checkout, branch creation, merge, staging,
commit, remote change, history rewrite, cleanup, service start, data read, or
`.git` operation.

The audit did not read values or contents from environment files, password
markers, databases, uploads, logs, output, or temporary PDFs. Those assets were
classified only by path, count, and aggregate size.

No current remote server state was queried. All `origin/*` findings below are
local remote-tracking snapshots and reflog evidence, not a claim about the
GitHub server at report time.

## 3. Repository Identities

| Property | Outer repository | Nested PA repository |
| --- | --- | --- |
| Worktree | `/Users/mac/Downloads/WeKnora-main` | `/Users/mac/Downloads/WeKnora-main/pa-ai-workbench` |
| Git directory | outer `.git/` directory | nested `.git/` directory |
| Current branch | `main` | `weknora-first-mvp` |
| Current HEAD | `554967030b13d674c533500106b06af69041b2f5` | `e3402c7ac0667a1a3c8282b668997693b9a4d170` |
| Upstream | `origin/main` | `origin/weknora-first-mvp` |
| `origin` URL | same PA GitHub SSH repository | same PA GitHub SSH repository |
| Worktrees | one | one |
| Registered submodules | none | none |
| Stash | none | one protected stash at `a4231cb` |

Exactly two `.git` directories were found:

```text
./.git
./pa-ai-workbench/.git
```

The outer repository records `pa-ai-workbench` as an ordinary `040000 tree`,
not a `160000` Git submodule. There is no `.gitmodules` contract. Both Git
repositories independently track the same physical PA files.

## 4. Commit and History Map

### 4.1 Divergent histories

The histories share PA history through `1b183e3`, then diverge:

```text
shared PA history ... -> 1b183e3

nested:
1b183e3
  -> c791ed1  complete native full completion sync
  -> b8a9e82  refresh document processing status
  -> d02519d  complete native intelligent dialogue stage
  -> e3402c7  streamline intelligent dialogue experience

outer:
42a6f0a  initialize WeKnora native baseline ----+
                                                  +-> 340356b
1b183e3  imported PA history -------------------+      -> 5549670
                                                          -> e7b258c
```

Exact divergence facts:

- `5549670...e7b258c = 0 / 1`.
- `1b183e3...e3402c7 = 0 / 4`.
- Across both object stores, `e7b258c...e3402c7 = 4 / 4`.
- `e7b258c` and `e3402c7` are not ancestors of each other.
- The outer object store does not know `e3402c7`.
- The nested object store does not know `e7b258c`.

### 4.2 Exact tree synchronization

| Outer PA subtree | Tree id | Equal nested root tree |
| --- | --- | --- |
| `340356b:pa-ai-workbench` | `789b0278...` | `1b183e3^{tree}` |
| `5549670:pa-ai-workbench` | `cb51dd09...` | `c791ed1^{tree}` |
| `e7b258c:pa-ai-workbench` | `c053ea532aabac1614e10c4f37e2863d46f3fcf1` | `e3402c7^{tree}` |

The final equality is the central baseline proof:

```text
outer e7b258c:pa-ai-workbench = c053ea532aabac1614e10c4f37e2863d46f3fcf1
nested e3402c7^{tree}          = c053ea532aabac1614e10c4f37e2863d46f3fcf1
```

Both trees contain 520 tracked files. This proves complete PA content equality,
including the final WNID dialogue optimization, without assuming equivalence
from filenames or working-tree appearance.

### 4.3 Candidate commit composition

`e7b258c` is one commit ahead of outer `main` and changes 87 files: 34 modified
and 53 added, with 19,819 insertions and 344 deletions.

| Group | Files | Meaning |
| --- | ---: | --- |
| Outer/native and shared infrastructure | 17 | Native Agent/MCP/Web Search/Wiki references, tests, router/types, Compose, built-in Agent config, and ignore rule |
| PA backend application | 14 | WNID API, services, schemas, history, audit, MCP, Web Search, AgentQA and chat integration |
| PA backend WNID scripts | 16 | Acceptance, browser, Quick Q&A, ReACT, MCP, Web Search, Wiki and local safe MCP tooling |
| PA WNID documents | 17 | Spec, parity, acceptance, task evidence, browser matrix and final report |
| PA frontend | 7 | Dialogue page and product-shell/history/library styling and API integration |
| PA knowledge engine | 1 | Native adapter integration |
| PA repo-local Skill | 2 | WNID Skill and generated metadata |
| Personal/resume materials | 13 | Personal Markdown and Word assets; privacy decision required |

The 17 outer/native paths are:

```text
.gitignore
config/builtin_agents.yaml
docker-compose.yml
internal/agent/act.go
internal/agent/act_references_test.go
internal/agent/tools/wiki_write_page.go
internal/application/service/mcp_service.go
internal/application/service/mcp_service_execution_test.go
internal/handler/mcp_service.go
internal/handler/mcp_service_ssrf.go
internal/handler/mcp_service_ssrf_test.go
internal/handler/web_search_provider.go
internal/mcp/client.go
internal/mcp/client_prompt_test.go
internal/router/router.go
internal/types/interfaces/mcp_service.go
internal/types/mcp.go
```

The current physical native files remain at `5549670`. Four native files added
by `e7b258c` are absent from the physical checkout, and the other candidate
native paths still have their outer-main blobs. The current checkout therefore
must not be used as WNID live-baseline evidence.

### 4.4 History that is not yet protected by the outer repository

The outer content snapshot does not preserve these nested commit objects:

```text
c791ed1
b8a9e82
d02519d
e3402c7
```

The nested repository also has:

```text
refs/stash = a4231cb53cd25ae596a221b110e95962bb7ca393
summary    = typed knowledge backend errors
path       = knowledge_engine/errors.py
```

Only `refs/stash` protects that stash. It is not an ancestor of nested HEAD.
It must be preserved and reviewed separately; this audit does not infer whether
later commits supersede it.

The outer repository also contains Codex snapshot/turn-diff refs and auxiliary
unreachable objects. Reachable-object connectivity passes, but neither object
database may be pruned or garbage-collected before the preservation task.

## 5. Physical Worktree Classification

Counts below use file-level untracked and ignored inventory rather than the
directory-collapsed default status view.

| State | Outer repository | Nested repository |
| --- | ---: | ---: |
| Tracked files | 2,326 | 520 |
| Staged | 0 | 0 |
| Modified tracked | 21 | 0 |
| Deleted tracked | 0 | 0 |
| Untracked files | 57 before this report, 58 including this report | 3 before this report, 4 including this report |
| Ignored files | 8,721 | 8,672 |

The outer `main` index tracks 471 PA paths. The nested HEAD tracks 520:

- 450 common paths have equal blobs and modes.
- 21 common paths have newer nested content:
  - 14 backend application files;
  - 6 frontend files;
  - 1 knowledge-engine adapter file.
- Nested HEAD adds 49 tracked paths:
  - 16 backend WNID scripts;
  - 17 WNID documents;
  - 13 personal/resume documents;
  - 2 repo-local Skill files;
  - 1 Dialogue page.

This accounts for the apparent outer dirtiness. The PA source is clean in the
nested repository and exactly matches the PA subtree in `e7b258c`; it is not a
random collection of unsaved edits. The outer view is dirty because it compares
that newer physical PA tree with the older `5549670` outer index.

The current PAR governance artifacts are not in either candidate commit:

```text
docs/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md
docs/PA_REPOSITORY_BASELINE_MAP_PAR_0_02.md
.github/skills/pa-repository-architecture-reorganization/SKILL.md
.github/skills/pa-repository-architecture-reorganization/agents/openai.yaml
```

The matching outer `.agents` Skill mirror is ignored local tooling. These files
must be added to the future frozen baseline without overwriting either source
history.

## 6. Tracked Source and Ownership Inventory

### 6.1 WeKnora native platform source

The outer repository tracks 1,855 files outside `pa-ai-workbench`. Major areas
include native `internal`, root `frontend`, `cli`, `migrations`, platform docs,
`docreader`, `client`, `mcp-server`, `config`, `helm`, `cmd`, `skills`, scripts,
and deployment assets.

This is the WeKnora platform source set. It must move as a controlled whole to
`platform/weknora`; selecting only `internal` would omit build, migration,
frontend, connector, CLI, MCP, documentation, and deployment dependencies.

### 6.2 PA product source

The nested repository tracks:

| Area | Tracked files | Target ownership |
| --- | ---: | --- |
| `backend` | 213 | `apps/pa-api` |
| `docs` | 145 | product/stage/evidence/archive classification |
| `knowledge_engine` | 55 | `packages/knowledge-engine/knowledge_engine` |
| `agent` | 48 | `packages/agent-runtime/agent` |
| `frontend` | 27 | `apps/pa-web` |
| `.github` | 19 before PAR additions | root repo-local development Skills |
| `scripts` | 3 | root dev/ops command surface |
| root product files | 10 | PA-first root metadata and historical specs |

The outer `frontend/` and nested `pa-ai-workbench/frontend/` are distinct
products. The former is WeKnora's native management UI; the latter is PA's
React workbench. They must become `platform/weknora/frontend` and `apps/pa-web`
respectively and must never be merged by basename.

### 6.3 Skill namespaces

Three Skill namespaces have different runtime meaning:

| Current path | Meaning | Migration rule |
| --- | --- | --- |
| outer `skills/` | WeKnora runtime Agent Skills | remain inside the native platform subtree |
| nested `agent/skills/` | PA workflow assets | remain with PA agent runtime |
| nested `.github/skills/` | versioned Codex development Skills | move to root `.github/skills` |
| outer `.agents/skills/` | local Codex Skill mirrors | preserve locally; keep mirrors synchronized |

They are not duplicate caches and must not be collapsed into one directory.

## 7. Local, Private, Personal, and Regenerable Assets

No content was opened for the items in this section.

### 7.1 Private runtime assets

| Path class | Count/size | State | Required treatment |
| --- | --- | --- | --- |
| PA `backend/data` | one database; directory 2.0M | ignored | private runtime; back up outside Git |
| PA `backend/uploads` | 8 files; 48K | ignored | private/raw input; do not inspect or publish |
| PA `logs` | 6 files; 7.4M | ignored | private runtime; do not migrate into Git |
| outer `tmp/pdfs` | 16 files; 6.4M | ignored | private temporary output |
| outer `output/pdf` | 1 file; 312K | untracked, not ignored | classify in `PAR-P3-02`; do not delete now |
| root and backend environment files | present | ignored | preserve values locally; never stage or print |
| root password marker | present | ignored | preserve privately; never stage or print |

Database, upload, log, output, and temporary directories may contain business
or personal data. They require a private backup/migration manifest, not a file
move into the canonical repository.

### 7.2 Regenerable assets

| Path | Files/size | Treatment |
| --- | --- | --- |
| PA `frontend/node_modules` | 5,911 files; 104M | rebuild from lockfile |
| PA `backend/.venv` | 2,399 files; 49M | rebuild from requirements |
| Python caches | 342 files | recreate automatically |
| PA `frontend/dist` | 3 files; 396K | rebuild |
| root `.pnpm-store` | 4 files; 48K | local cache |

Current outer `main` does not ignore `.pnpm-store`; candidate `e7b258c` adds
that ignore rule. `output/` remains an explicit later hygiene decision. No
regenerable asset is deleted in this task.

### 7.3 Personal materials

`pa-ai-workbench/docs/resume_project` contains 13 tracked files totaling about
580K: 9 Markdown files and 4 Word documents.

They are present in nested `e3402c7` and therefore in the identical PA subtree
of outer candidate `e7b258c`. Local reflogs record both branches being pushed on
2026-06-29, but this audit did not contact the remote and cannot state current
server visibility or repository privacy.

Before a candidate becomes canonical, the user must choose one of:

1. retain them in a confirmed private repository;
2. export them to a private archive and remove them in an explicit reviewed
   commit;
3. keep a sanitized approved subset.

They must not be silently deleted, moved into a public root, or republished by
repository reorganization.

## 8. Command, Build, Workflow, and Documentation Inventory

### 8.1 Command surface

Scripts currently span:

- 21 outer scripts, including `pa-workbench-setup`, `start`, and `check`;
- 3 nested PA service/LaunchAgent scripts;
- 140 PA backend check, smoke, configure, and run scripts.

There are no exact basename collisions across the major groups, but there is
semantic fragmentation. The root launcher hardcodes
`$ROOT_DIR/pa-ai-workbench`, then delegates to nested `pa-dev-services.sh`.
The future command surface must classify these by dev, ops, release, and
validation rather than deleting similar-looking scripts.

### 8.2 Compose, Docker, and workflows

- Two Compose files exist, both at the outer WeKnora root.
- Five Dockerfiles exist, all for native/platform components.
- Four GitHub workflows exist, all at the outer root and oriented around native
  UI, app, docreader, sandbox, CLI, and lite release paths.
- The nested PA project has no PA Dockerfile, Compose service, or GitHub
  workflow. It starts PA API/Web as local processes.

The root Compose and workflows assume WeKnora is at repository root. Their
contexts and working directories include `.`, `./frontend`, `docker/*`, `cli`,
and `frontend`. They cannot simply be renamed after relocation.

Native `docker/Dockerfile.docreader` uses `COPY packages/ /app/packages/`.
The target PA-first root also creates `packages/`. If the native build context
remains `.`, Docker can silently copy PA packages into a native image. Native
build contexts must be rooted at `platform/weknora` before root PA packages are
introduced. The current root `.dockerignore` also does not exclude the nested
PA tree, so current native app builds may send it into the build context.

### 8.3 Documentation

- Outer platform docs: 95 files.
- PA docs after this report: 147 physical files, including 145 previously
  tracked files, the PAR Spec, and this report.
- PA backend validation scripts: 140.
- WNID-related files across code, scripts, docs, UI, and Skill: 32.

PA docs are largely flat and mix product specs, stage specs, acceptance,
reports, evidence, architecture, runbooks, final handoff, and personal assets.
The outer root README still presents WeKnora as the product, while the nested
README presents PA AI Workbench. This confirms the product-root mismatch the
PAR stage must resolve.

## 9. Path, Import, and Runtime Dependency Map

### 9.1 Python package risk

Committed nested `e3402c7` contains:

```text
114 Python files that infer PROJECT_ROOT with Path(...).parents[2]
96 Python files that mutate sys.path or PYTHONPATH
164 Python files that directly import agent or knowledge_engine
```

Moving a script from `backend/scripts` to `apps/pa-api/scripts` changes the
repository-root depth. The target distribution directories
`packages/agent-runtime` and `packages/knowledge-engine` also contain hyphens,
which cannot replace the Python imports.

The safe target is:

```text
packages/agent-runtime/agent/...
packages/knowledge-engine/knowledge_engine/...
```

with `pyproject.toml` workspace/install metadata preserving the import
contracts. Packaging must precede removal of path injection.

### 9.2 Absolute and old-root references

In committed nested `e3402c7`:

- 43 files contain a `/Users/mac/` path;
- 53 files contain `pa-ai-workbench`;
- a narrower physical scan found 28 files containing the complete current
  workspace root string.

Outer candidate `e7b258c` contains 61 files with `pa-ai-workbench` references.
Some are historical evidence and should stay historically truthful; active
Spec, Skill, checker, runbook, launcher, and configuration paths must migrate.

The 17 WNID documents all reference `backend/scripts`; 13 contain absolute
paths, 12 reference outer `internal/...`, and 9 reference `frontend/src/...`.
The WNID acceptance scripts also assume sibling checker imports and fixed
`docs`/`backend/scripts` locations. Move that validation suite as a group or
introduce explicit repository path configuration before moving individual
files.

### 9.3 Frontend and API boundaries

PA React uses `VITE_API_BASE_URL` with a default PA BFF at port 8000 and exposes
PA `/api/...` contracts. WeKnora native UI uses `/api/v1/...` and its native app
at port 8080. Both frontend development servers can default to port 5173.

The reorganized command and reverse-proxy layers must use distinct service
names and ports. PA frontend must continue calling the PA BFF; it must not be
rewired directly to native `/api/v1` routes. The adapter should receive the
native service base URL without duplicating the `/api/v1` prefix.

### 9.4 Links and Skill paths

Current WNID Spec/report links mostly assume one flat docs directory. Moving
Specs into `docs/stages` and evidence into `docs/evidence` will break those
relative links unless migrated together.

Existing PA Skills encode the current nested working directory, Spec path,
repo-local Skill path, and outer `.agents` mirror path. The eventual Skill move
must update every affected PA Skill and run a full link/path checker, not only
the new PAR Skill.

## 10. Remotes and Ref Preservation Map

### 10.1 Configured remotes

The outer repository has:

- `origin`: the PA GitHub SSH repository;
- `pa-ai-workbench`: the local nested repository path.

The nested repository has:

- `origin`: the same PA GitHub SSH repository.

No Tencent WeKnora upstream remote is configured. Upstream attribution and a
clear `weknora-upstream` role remain required before final release.

### 10.2 Local remote-tracking snapshots are inconsistent

| Ref snapshot | Local value |
| --- | --- |
| outer `origin/main` | `5549670` |
| nested `origin/main` | `36ea9ca` |
| outer `origin/weknora-first-mvp` | `bb3dc59` |
| nested `origin/weknora-first-mvp` | `e3402c7` |
| outer local-remote sprint snapshot | `1b183e3` |
| outer `origin/codex/weknora-agent-learning-skill` | `e7b258c` |

These snapshots were updated at different times. No canonical decision may use
them as current server truth until an explicitly scoped remote verification.

### 10.3 Minimum protected set

Before any nested-Git removal or history integration, preserve and verify:

```text
outer main                                    5549670
outer codex/weknora-agent-learning-skill     e7b258c
nested weknora-first-mvp                     e3402c7
nested d02519d and the complete post-1b chain
nested m1-ready-20260609 tag
nested refs/stash                            a4231cb
outer Codex snapshot and turn-diff refs
current PAR governance artifacts
all classified private, personal, and runtime assets
```

## 11. Recommended Freeze Input for PAR-P0-01

The evidence-backed recommendation is:

| Role | Source |
| --- | --- |
| Complete coherent content candidate | outer `e7b258c` |
| Original post-`1b183e3` PA commit history | nested `e3402c7` ancestry |
| Uncommitted governance delta | current PAR Spec, report, Skill and metadata |
| Independent hidden change | nested `refs/stash` |
| Private/local state | classified runtime and personal inventory |

`PAR-P0-01` should:

1. Create verified recovery artifacts for both Git stores and all protected
   refs, including the stash, without deleting current stores.
2. Materialize `e7b258c` in a separate worktree or temporary clone. Do not
   switch the current hybrid worktree, where outer-untracked paths overlap the
   candidate tree.
3. Bring the original nested commits into a protected namespace in the outer
   object database and verify reachability. Any history-only merge or other
   canonical reachability mechanism requires its own reviewed plan.
4. Add the PAR governance artifacts without absorbing private runtime data.
5. Resolve the personal-material publication decision before canonical push or
   release.
6. Run the pre-reorganization static, build, native, PA, live workflow, and
   browser acceptance suite from the coherent candidate.
7. Only after those gates pass, propose a canonical branch and recovery
   procedure for `PAR-P0-02`.

This task does not authorize those writes.

## 12. Approval Gates

Explicit user approval or a later scoped task is required before:

- updating/fetching remote refs for canonical selection;
- creating preservation branches, tags, bundles, or history-integration
  commits;
- checking out a different branch in the current worktree;
- changing remotes;
- moving or removing either `.git` directory;
- moving, publishing, sanitizing, or deleting personal materials;
- deleting private runtime or regenerable assets;
- staging, committing, merging, or pushing.

## 13. Validation Evidence

| Check | Result |
| --- | --- |
| Required outer/nested status, recent log, and remote inventory | PASS |
| Two-Git-root and ordinary-tree/no-submodule proof | PASS |
| Outer/nested branch, tag, stash and worktree inventory | PASS |
| Exact candidate PA subtree vs nested root tree comparison | PASS; identical `c053ea53...` |
| Candidate/native delta and PA delta classification | PASS; 17 native plus complete 520-file PA tree |
| Ref ancestry and missing-object checks | PASS for audit; confirms history preservation is still required |
| Reachable-object connectivity in both repositories | PASS; auxiliary/dangling objects remain protected from pruning |
| Candidate and nested tracked diff whitespace checks | PASS |
| Tracked unsafe-artifact name scan | PASS; only versioned environment examples matched |
| Tracked/untracked/ignored and runtime-size inventory | PASS |
| Absolute path, old-root, packaging, Compose, workflow and Skill scans | PASS |
| PAR Skill validation and mirror equality | PASS |
| New report/Spec whitespace, placeholder, and sensitive-assignment scans | PASS |

Evidence limits:

- No current remote server state was verified.
- No product build, service, browser, or live workflow was run because the
  physical checkout is intentionally identified as a mixed baseline.
- No canonical ref was selected or changed.

## 14. Final Decision

`PAR-0-02` is complete as read-only repository inventory and baseline-map
evidence.

Outer `e7b258c` is the strongest coherent content candidate because it exactly
contains nested PA `e3402c7` plus the native WNID patch. It is not yet the
canonical branch. Nested history, stash, personal materials, runtime assets,
auxiliary refs, and current PAR artifacts remain protected.

The next task is `PAR-0-03`: add a deterministic repository-reorganization
acceptance harness before freezing or moving the baseline.
