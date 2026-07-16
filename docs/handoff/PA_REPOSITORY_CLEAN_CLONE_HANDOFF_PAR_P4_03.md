# PA Repository Clean-Clone Handoff — PAR-P4-03

Date: 2026-07-15
Decision: PASS
Task: `PAR-P4-03 — Clean-clone final acceptance and handoff`

## Scope and candidate identity

This acceptance closes the PAR repository-architecture stage. The candidate is
the exact Git index of the source workspace, not the source working tree. The
checker exports that index into a temporary seed repository, commits only in
the seed, and performs a real local clone into a second temporary directory.
This preserves and excludes all unstaged or untracked user work while proving
that the staged repository candidate is reproducible.

No source commit, push, merge, branch change, history rewrite, Docker rebuild,
or existing service lifecycle change was performed. Temporary repositories,
isolated SQLite/uploads, build output, and PA process state are removed after
acceptance.

## Canonical repository and versions

| Contract | Canonical value |
| --- | --- |
| Repository identity | PA AI Workbench |
| Canonical origin | `git@github.com:wjr1314lxj-star/pa-ai-workbench.git` |
| PA API version | `0.1.0` |
| PA Web version | `0.1.0` |
| Controlled WeKnora version | `0.6.0` |
| Product ownership | PA apps/packages at root; WeKnora under `platform/weknora` |

The controlled WeKnora import provenance and PA delta remain governed by
`platform/weknora/UPSTREAM.md`, `platform/weknora/PA_PATCHES.md`, and
`THIRD_PARTY_NOTICES.md`.

## Canonical commands

Run from the repository root:

```bash
make setup
make start
make status
make validate
make validate-live-acceptance
make validate-clean-clone
make validate-par-final
```

`make setup` creates the ignored root Compose environment, the platform
development compatibility environment, the canonical PA runtime environment,
and the PA Web local environment from public examples. It installs backend and
frontend dependencies using npm, or pnpm when npm is unavailable.

`make start` is the documented state-changing full-stack command. During this
acceptance, the existing user-owned WeKnora Compose project remained untouched;
the cloned PA API and Web processes were started with `--skip-weknora`, isolated
ports, an isolated database, and isolated uploads. The clone then reused the
already-running configured WeKnora service for live workflow/browser proof.

## Clean-clone acceptance matrix

| Gate | Result | Evidence |
| --- | --- | --- |
| Exact candidate export | PASS | Source index exported; unstaged/untracked work excluded |
| Real clone and Git topology | PASS | Temporary seed committed locally; second checkout cloned; exactly one `.git` |
| Tree identity and cleanliness | PASS | Source index tree equals cloned commit tree; checkout clean before and after validation |
| Fresh setup | PASS | Root/platform/PA/Web examples created; Python and Node dependencies installed |
| Static and build | PASS | Root command/Python/backend/Web/static/PAR validation; Web output under `/tmp` |
| Compose model | PASS | Canonical root Compose config renders without service mutation |
| Start, status, and health | PASS | Isolated cloned PA API/Web started; health, PA status, native status, and Web returned HTTP 200 |
| Core live workflows | PASS | Document/RAG/dialogue/ReACT/Wiki/MCP/Web/history/citation/audit matrix |
| Browser acceptance | PASS | Seven PA routes at desktop/mobile plus WNID dialogue viewports |
| Resource cleanup | PASS | Temporary knowledge bases/Agents zero; isolated clone runtime removed |
| Final governance | PASS | `make validate-par-final` passes inside the fresh clone |
| Source/service preservation | PASS | Source history/origin unchanged; existing `weknora-main` service not stopped or rebuilt |

The executable evidence is
`scripts/validation/check_pa_repository_clean_clone_acceptance.py`, exposed as
`make validate-clean-clone`. It intentionally prints only phase/decision
metadata and never credentials, private endpoints, provider payloads, raw
documents, answers, or generated identifiers.

The external-provider portion has one bounded full-matrix retry for transient
network/provider failures. A PASS still requires one complete successful live
attempt followed by zero temporary knowledge bases and Agents; two failures
remain a hard non-zero result.

## Preserved user work

The clean-clone candidate deliberately excludes and leaves unchanged:

- the unstaged modification in `apps/pa-api/app/database.py`;
- the unstaged modification in `scripts/dev/pa-workbench-start.sh`;
- the untracked `tests/backend/test_database_runtime_path.py`;
- protected personal material under `docs/resume_project`;
- ignored environments, databases, uploads, logs, caches, outputs, vectors,
  credentials, and other local runtime state.

## Remaining backlog and limits

- The source workspace still contains the intentionally uncommitted PAR index;
  source commit/push/merge was outside the authorized task.
- Three broad unfiltered upstream/native Go residual domains recorded by
  PAR-P4-01 remain controlled upstream/external-environment limitations; the
  passing controlled native build/test matrix remains the acceptance contract.
- The host default shell does not provide Go or Helm CLIs. No new Go/Helm PASS
  is claimed by this clean-clone run; PAR-P4-01 contains the truthful build and
  static Helm evidence.
- Protected personal material remains intentionally outside repository
  architecture ownership until the user chooses a destination.

## Release-owner handoff

PAR has no remaining task. The next release task is **release-candidate review
and publication**: the repository owner should review the staged candidate,
decide the release/version policy, create an explicit commit, push it, and run
remote CI/release gates. Those actions require separate authorization and were
not performed here.
