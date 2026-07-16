# PAR-P1-01 WeKnora Platform Relocation Evidence

> Date: 2026-07-14
>
> Task: `PAR-P1-01`
>
> Status: `[x]` validated complete
>
> Decision: `PASS`
>
> Evidence type: `git-move + static + build-path + Go test`

## 1. Result

The complete PA-controlled WeKnora native platform is now located at:

```text
/Users/mac/Downloads/WeKnora-main/platform/weknora
```

The move preserves WeKnora as the native owner of RAG, Document, Wiki,
AgentQA, MCP, Web Search, model/config, parser, vector-store, data-source,
native UI, CLI/SDK, and deployment capabilities. PA API, PA Web, PA Agent
Runtime, and PA Knowledge Engine remain unchanged under `pa-ai-workbench/`;
their promotion is still `PAR-P1-02`.

No branch was switched, no commit was created, no remote was changed, and
nothing was pushed or merged. Existing PA product modifications and untracked
WNID/PAR evidence remain preserved.

## 2. Migration Boundary

The controlled native tree moved as one ownership boundary, including:

```text
cmd/ internal/ client/ cli/ frontend/ docreader/ mcp-server/
config/ migrations/ dataset/ skills/ testdata/ tests/ examples/
miniprogram/ misc/ packages/ docker/ deploy/ helm/ scripts/ docs/
.github/ Makefile go.mod go.sum native root metadata and license files
```

The source-side move was file-granular: only Git tracked paths were passed to
`git mv`. This avoided recursively moving ignored/untracked `.env`, database,
upload, log, output, cache, dependency, vector, or personal data that happened
to be physically below an old directory shell.

Explicitly outside the move:

- `pa-ai-workbench/backend`, `frontend`, `agent`, and `knowledge_engine`;
- `pa-ai-workbench/docs/resume_project`;
- `.agents`, `.codex`, `.pnpm-store`, `output`, and `tmp`;
- root `.env`, password marker, PA databases/uploads/logs, dependency caches,
  and all other local-only runtime assets.

## 3. Pre-Move and Post-Move Inventory

| Checkpoint | Evidence |
| --- | --- |
| Current-index native source before move | 1,855 tracked files outside `pa-ai-workbench`; NUL path-list SHA-256 `fb9a92d231edd0cbf369999db50a0f74decfa8bba0187e0362939590c4e5d213` |
| Current native worktree cleanliness before move | PASS; `git diff --quiet -- . ':(exclude)pa-ai-workbench/**'` |
| Pure-move index checkpoint | 1,855 `R` entries with rename detection at 50%; no cached PA app/package path |
| Final staged view | 1,854 `R`, 9 `A`, and 1 `M`: recreating the root safety `.gitignore` makes Git retain that path as modified and represent the native `.gitignore` as added; the other additions are the four WNID files, two attribution files, the PAR Spec, and this report |
| Coherent native baseline | 1,859 files outside the PA subtree at `par-p0-01-coherent-baseline-20260714`; four WNID native files are additive to current `main` |
| Target before attribution | 1,859 files; every coherent-baseline native blob matched at the new relative path before path-only adjustments |
| Target after attribution | 1,861 files: 1,859 controlled baseline files plus `UPSTREAM.md` and `PA_PATCHES.md` |
| Old tracked native source roots | PASS; no tracked path remains outside `.gitignore`, `pa-ai-workbench/**`, and `platform/weknora/**` |
| Physical old directory shells | Some empty or ignored/untracked shells remain, but every scanned shell reports `tracked=0`; they were not deleted because they may contain user-local state |

The four coherent-baseline files added at the new path are:

```text
internal/application/service/mcp_service_execution_test.go
internal/handler/mcp_service_ssrf.go
internal/handler/mcp_service_ssrf_test.go
internal/mcp/client_prompt_test.go
```

The other native WNID files were restored to their coherent-baseline blobs
after the move. This prevents the active PA WNID product code from being paired
with the older native `main` implementation.

## 4. Native Integrity and Go Paths

- The module root is now `platform/weknora/go.mod` and still declares
  `github.com/Tencent/WeKnora`.
- Native Go imports remain module imports; no repository-folder prefix was
  added and no broad import rewrite was required.
- `platform/weknora/cli/go.mod` still replaces
  `github.com/Tencent/WeKnora/client` with `../client`, which remains valid.
- `go:embed` assets remain inside the moved module and `go list ./...` resolves
  all packages from the new root.
- Before path-only workflow/launcher edits, all 1,859 native baseline blobs
  matched the coherent tag. After the edits, only four workflow files and two
  legacy PA helper launchers differ, exactly for new-root resolution. Native Go
  source remains the coherent-baseline implementation.

## 5. Direct Path Adjustments

Only relocation-caused adjustments were made:

1. Four imported native workflow files now use `platform/weknora/` in path
   filters, Go working directories, cache paths, Docker contexts, Dockerfile
   paths, and release artifact locations.
2. `scripts/pa-workbench-setup.sh` and `scripts/pa-workbench-start.sh` now find
   the unchanged `pa-ai-workbench/` tree through the monorepo root while
   retaining the native directory as their WeKnora root.
3. The root `.gitignore` is a temporary safety shim. The imported native ignore
   policy moved to `platform/weknora/.gitignore` and includes `.pnpm-store/` from
   the coherent baseline.
4. [`UPSTREAM.md`](../../platform/weknora/UPSTREAM.md) and
   [`PA_PATCHES.md`](../../platform/weknora/PA_PATCHES.md) record upstream
   identity, the missing exact-upstream-SHA limitation, controlled baseline,
   WNID exception paths, ownership guardrails, and future sync validation.

No Compose topology, service behavior, script taxonomy, documentation
taxonomy, Go package design, or PA application path was reorganized.

## 6. Validation Evidence

| Gate | Result |
| --- | --- |
| Go module/package scan | PASS in cached `golang:1.26.0` container with source mounted read-only: `go env GOMOD` = `/src/go.mod`; `go list ./...` enumerated the new module |
| Native focused Go tests | PASS: `./internal/agent/...`, `./internal/application/service`, `./internal/handler/...`, `./internal/mcp/...` |
| Client module | PASS: `go test -count=1 ./...` from `/src/client` |
| CLI module | PASS: `go test -count=1 ./...` and `go vet ./...` from `/src/cli` |
| Shell syntax | PASS: native scripts, cloud-image scripts, and docreader generator pass `bash -n` |
| Workflow YAML | PASS: all four imported workflow files parse as YAML |
| Full Compose | PASS with `.env.example` interpolation and `--no-env-resolution`; real `.env` was not read |
| Dev Compose | PASS with `.env.example` interpolation and `--no-env-resolution` |
| Compose build context | PASS: app and docreader resolve to `/platform/weknora`; frontend resolves to `/platform/weknora/frontend` |
| Dockerfile COPY sources | PASS: Go module files, `cmd/download`, native `packages/`, docreader files, and frontend package/build files exist in their declared contexts |
| `COPY packages/` collision guard | PASS: `Dockerfile.docreader` uses the isolated `platform/weknora` context, so future root PA `packages/` cannot be copied silently |
| Old tracked native path scan | PASS: zero tracked old-root native source paths |
| PA module move guard | PASS: zero cached changes under PA backend/frontend/agent/knowledge_engine; the pre-existing 21 PA modified files remain unstaged user work |
| Attribution completeness | PASS: required native capability ownership, baselines, upstream URL/module/license/version, patch paths, shims, and `PAR-P3-03` follow-up are present |
| PAR checker self-test | PASS: positive final fixture and negative required gates |
| PAR checker governance mode | PASS: one Git root and governance ready |
| PAR checker final mode | Expected FAIL only for later-stage boundaries/evidence after this report and Spec update; see final command evidence below |
| Skill validation | PASS for repo-local and `.agents` skill copies |
| Skill mirror comparison | PASS for `SKILL.md` and `agents/openai.yaml` |
| Git whitespace checks | PASS for staged and unstaged task deltas |
| Sensitive-pattern scan | PASS for new/edited PAR-P1-01 artifacts; no credential values, private keys, private endpoints, raw documents, databases, logs, provider payloads, or vectors were added |

The Go validation container downloaded public module dependencies because the
host exposes no Go binary or module cache. It did not install host software and
mounted `platform/weknora` read-only.

Final checker execution remains expectedly non-zero and reports only these
later-stage codes:

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

Its missing-boundary detail starts with `apps/pa-api`, `apps/pa-web`, PA
packages, `infra`, canonical scripts/tests/docs, and root product files. It no
longer names `platform/weknora`, `UPSTREAM.md`, or `PA_PATCHES.md` as missing.

## 7. Attribution Decision

`UPSTREAM.md` records the locally provable upstream identity:

```text
repository      https://github.com/Tencent/WeKnora
module          github.com/Tencent/WeKnora
version marker  0.6.0
local import    42a6f0ac810dd04a64a6b0999b06554ac76a5e0b
coherent ref    e7b258c61d56bd44ce477ef29cf761d8ab07cdfc
```

The exact Tencent upstream commit behind the flattened local import is not
present in the current lineage. The report and ledger state this limitation
truthfully; `PAR-P3-03` must verify and finalize that SHA, an upstream remote,
and third-party notice reconciliation.

## 8. Compatibility Shims and Residual Risk

| Item | Current treatment | Removal/finalization task |
| --- | --- | --- |
| Root `.gitignore` | Temporary safety shim protects PA/local runtime work after native ignore rules moved | `PAR-P3-02` |
| Imported native workflows below `platform/weknora/.github` | Internal paths are new-root-correct, but GitHub discovers canonical workflows only at root | `PAR-P2-02` moves/consolidates them; no fake active-CI claim is made |
| Imported root/native Compose, Docker, Helm layout | Kept together under the controlled platform so native contexts work | `PAR-P2-02` consolidates canonical infrastructure |
| Imported scripts, including PA helper launchers | Kept with the imported source; two helpers have a documented monorepo-root locator | `PAR-P2-03` consolidates command surfaces |
| Imported native and mixed historical docs | Moved without taxonomy rewrite | `PAR-P3-01` classifies product, architecture, evidence, and archive docs |
| Empty/ignored old directory shells | Preserved because they may contain local artifacts; tracked native files are zero | `PAR-P3-02` classifies runtime residue without deleting user data |
| Exact upstream source SHA | Unknown from current history; no value invented | `PAR-P3-03` |

The PA product is still physically nested under `pa-ai-workbench/`; this is the
expected next boundary, not a `PAR-P1-01` failure.

## 9. Recovery Evidence

Recovery remains non-destructive:

- source content can be reproduced from
  `par-p0-01-coherent-baseline-20260714` at `e7b258c`;
- P0-01 and P0-02 verified bundles/full Git snapshots remain under their
  owner-only ignored recovery directories;
- the pure-move checkpoint is visible as 1,855 Git rename entries;
- the imported nested PA history and stash remain reachable under
  `refs/archive/pa-nested/20260714/*`;
- current user work was not reset, checked out, cleaned, committed, pushed, or
  merged.

Recovery must be performed in a copied or isolated worktree from the protected
refs and reports; this task does not recommend applying a destructive reset to
the active mixed worktree.

## 10. Final Decision and Next Task

`PAR-P1-01` is complete. The controlled WeKnora platform is intact and usable
from `platform/weknora`, coherent WNID native patches are present, direct build
and workflow paths are repaired, attribution exists, and PA application/module
paths were not moved.

The next task is `PAR-P1-02`: promote PA API/Web/Agent Runtime/Knowledge Engine
into `apps/` and `packages/` without beginning Compose, command-surface, or
documentation consolidation early.
