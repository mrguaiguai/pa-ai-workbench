# PA Repository Runtime Artifact and Ignore Hygiene — PAR-P3-02

> Date: 2026-07-15
>
> Task: `PAR-P3-02`
>
> Type: docs/runtime hygiene — runtime and ignore boundary only
>
> Result: complete

## Scope and safety baseline

This task consolidates Git ignore ownership, establishes a canonical local PA
runtime boundary, preserves existing local state, and adds deterministic ignore
acceptance to the PAR checker. It does not read or migrate runtime payloads,
change native/product capability behavior, finalize upstream attribution, or
start P4 acceptance.

The starting baseline remained one Git root at `5549670` with the canonical
origin unchanged and all prior staged work preserved. The only canonical active
PAR Spec was under `docs/stages/current`. A same-named file under the ignored
`tmp/par-p0-01-validation` tree is a P0 isolated-validation snapshot, not an
active Spec; it was neither read nor modified.

No env value, credential, database body, upload, log, output body, cache,
vector, model payload, or personal-material content was opened. Inventory used
Git path metadata, file type/name checks, and directory existence only.

## Pre-change inventory

The metadata-only inventory found:

| Runtime class | Existing count | Disposition |
| --- | ---: | --- |
| non-example env files | 3 | retained in place and ignored |
| database/WAL/SHM files | 4 | retained in place and ignored |
| uploads and logs directories | 4 | retained in place and ignored |
| Python/test/Vite cache directories | 207 | retained; no cleanup performed |
| Node/venv/package-store directories | 3 | retained; no reinstall performed |
| dist/output/tmp/temp directories | 24 | retained; no cleanup performed |
| protected personal files visible before consolidation | 13 | retained in place; now precisely ignored |

There were zero visible non-personal untracked files before implementation.
The legacy PA tree contained two tracked governance/attribution files and no
unignored runtime or personal file.

## Implemented boundary

### Root ignore ownership

The root `.gitignore` is now the PA-wide policy for:

- real env files and credential-shaped files, while `.env.example` and
  `.env.*.example` remain visible;
- root `.local/`, databases, uploads, vectors, logs, pid files, root
  output/tmp/temp, Python caches, virtual environments, Node package stores,
  Vite/TypeScript caches, coverage, and targeted generated bundles;
- retained legacy PA runtime paths and the protected personal directory.

The obsolete nested `pa-ai-workbench/.gitignore` was removed after the root
rules proved equivalent coverage. Native-only rules remain owned by
`platform/weknora/.gitignore`.

The former `**/build/` and unanchored `output/` rules were deliberately removed.
They incorrectly hid legitimate native Go source below
`platform/weknora/cli/internal/build` and `internal/output`. Generated bundles
are now excluded by explicit root/app/native frontend and desktop binary paths.

### Canonical runtime

New local checkouts use:

```text
.local/pa-api
.local/pa-dev
```

PA API relative database/upload settings resolve below `.local/pa-api`.
Development pid/log state resolves below `.local/pa-dev`. Compose continues to
use named volumes or configured external storage.

Existing runtime is not automatically migrated. PA config, setup, process
management, and LaunchAgent installation use path-presence checks for retained
legacy env, venv, data, uploads, pid, and log state. When those markers exist,
the old location remains selected. This checkout therefore reports
`current_runtime=legacy_preserved_by_path_marker`; a fresh checkout defaults to
`.local/pa-api`. No service was restarted to apply a different location.

The policy and manual approval boundary are documented in
`docs/operations/LOCAL_RUNTIME_DATA.md`.

### Acceptance checker

The PAR checker now enforces two runtime properties in final mode:

1. private/runtime probes must be ignored;
2. env examples and legitimate native `internal/build`, `internal/output`,
   desktop resource, and PA storage source probes must remain visible.

Its self-test includes a complete ignore fixture and a negative overbroad or
missing-ignore fixture. `legacy_product_tree_present` now means the legacy tree
still contains tracked or unignored repository-visible entries, not merely
that an ignored directory with protected data physically exists.

After this task is staged, the remaining legacy tracked entry is the attribution
notice assigned to PAR-P3-03. Ignored runtime and personal data do not need to
be deleted for final acceptance.

## Validation evidence

### Ignore and preservation gates

| Check | Result |
| --- | --- |
| Required runtime ignore probes | PASS, 15/15 |
| Required source/example visibility probes | PASS, 8/8 |
| Tracked files accidentally matched by ignore policy | PASS, zero |
| Unsafe tracked runtime artifacts | PASS, zero |
| Legacy unignored entries | PASS, zero |
| Protected personal boundary | PASS, present, ignored, unread |
| Before/after runtime object counts | PASS, all six classes unchanged |
| Root `.dockerignore` context policy | PASS, deny-by-default unchanged |
| Compose example-env config | PASS, quiet mode; no real env loaded or printed |

### Static and product regression

| Check | Result |
| --- | --- |
| Changed shell `bash -n` and root shell validation | PASS |
| No-cache Python compile and root Python validation | PASS, 278 files |
| PA backend discovery | PASS, 3/3 |
| PA Web TypeScript/Vite build | PASS, 1,589 modules; output under `/tmp` |
| Root `make validate` | PASS |
| PAR checker governance, JSON, self-test, cross-root contract | PASS |
| WNID final checker | PASS, 17/17 |
| WNFC final checker | PASS, 14/14 and final ready |
| WNX acceptance | PASS, 30 reports |
| Deployment readiness | PASS, static mode |
| Setup/start help and LaunchAgent static syntax/path scan | PASS |
| PAR Skill quick validation and mirror comparison | PASS |
| Sensitive scan and staged/unstaged diff checks | PASS |

The host Go and Helm CLIs remain unavailable, so this task does not claim new
Go or Helm execution. Their P2 evidence is not reused as a current P3-02 run,
and full static/build acceptance remains PAR-P4-01.

### Service and Git safety

- Read-only Docker status reports the pre-existing `weknora-main` project
  `running(5)` from its historical Compose path.
- No container or LaunchAgent was installed, started, stopped, restarted,
  rebuilt, or migrated.
- One active Git root, HEAD, branch, and origin remain unchanged.
- No reset, checkout, rebase, cleanup, commit, push, merge, or history rewrite
  was performed.

## Recovery and residual risk

Recovery requires only reverting the explicit source/policy edits; runtime
payloads need no restoration because none were moved or deleted. Existing
legacy selection is intentionally conservative. A future user-approved data
migration must stop services, back up state, select exact source/destination
paths, and validate database/uploads before changing the marker-based fallback.

Residual work is intentionally separate:

1. `pa-ai-workbench/NOTICE.md` and upstream/native patch attribution belong to
   PAR-P3-03; this is why the final checker still reports the legacy tree.
2. `THIRD_PARTY_NOTICES.md` belongs to PAR-P3-03.
3. `tests/acceptance`, static/build final evidence, live workflows, and clean
   clone handoff belong to P4.

The next task is `PAR-P3-03`.
