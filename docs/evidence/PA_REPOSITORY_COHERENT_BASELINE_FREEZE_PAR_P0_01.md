# PAR-P0-01 Coherent Product and Runtime Baseline Freeze

> Date: 2026-07-14
>
> Task: `PAR-P0-01`
>
> Decision: `PASS`
>
> Evidence type: `git-integrity + static + build`
>
> Coherent content ref: `par-p0-01-coherent-baseline-20260714`

## 1. Result

The complete pre-reorganization PA plus WeKnora WNID source is frozen at:

```text
outer tag    par-p0-01-coherent-baseline-20260714
commit       e7b258c61d56bd44ce477ef29cf761d8ab07cdfc
root tree    7d5207c5dd1ec8a4ee8deb646a3f9b6cf70ae217
PA subtree   c053ea532aabac1614e10c4f37e2863d46f3fcf1
```

The PA subtree is exactly equal to the nested repository root at
`e3402c7ac0667a1a3c8282b668997693b9a4d170`. The same outer commit contains
the 17 native WNID changes identified by `PAR-0-02`. One ref therefore
materializes the complete coherent product/runtime content without using the
current hybrid checkout as evidence.

Both original Git stores remain in place. No branch was switched, merged, or
created; no commit was made; no remote was changed or queried; nothing was
staged or pushed; and neither `.git` directory was moved or removed.

## 2. Protection Refs

| Repository | Protection ref | Object |
| --- | --- | --- |
| Outer | `par-p0-01-outer-main-before-freeze-20260714` | `554967030b13d674c533500106b06af69041b2f5` |
| Outer | `par-p0-01-coherent-baseline-20260714` | `e7b258c61d56bd44ce477ef29cf761d8ab07cdfc` |
| Nested | `par-p0-01-nested-pa-head-20260714` | `e3402c7ac0667a1a3c8282b668997693b9a4d170` |
| Nested | `par-p0-01-nested-stash-20260714` | `a4231cb53cd25ae596a221b110e95962bb7ca393` |

The existing nested `m1-ready-20260609` tag and `refs/stash` remain unchanged.
The protection tags add names; they do not rewrite the referenced objects.

## 3. Recovery Set

Local recovery artifacts are stored under the ignored, permission-restricted
directory:

```text
/Users/mac/Downloads/WeKnora-main/tmp/par-p0-01-recovery/20260714
```

| Artifact | Purpose | Size | SHA-256 |
| --- | --- | ---: | --- |
| `outer-all-refs.bundle` | Portable outer refs and history, including Codex snapshot/turn-diff refs and both outer protection tags | 24,941,476 bytes | `12db148f67b51dbef86559de95a04e9ff6379bb90569787018d9c2e74c5d11b5` |
| `nested-all-refs.bundle` | Portable nested branches, remote snapshots, tag, stash, and both nested protection tags | 1,967,718 bytes | `5da86ec4bc3574af7dce7f88f1be3f1a9bc0d3ec9969a98fca938ab91aeb4b66` |
| `outer-git-dir.tar.gz` | Full outer `.git` fallback, including reflogs and objects not represented by ordinary branch/tag names | 38,185,609 bytes | `53ae1ab27a2f2b89fff7c39098220c6513ea154dcfbc93868411a4c4fa776348` |
| `nested-git-dir.tar.gz` | Full nested `.git` fallback, including the independent stash and reflogs | 10,442,167 bytes | `f51a0fc59dc3171becff28150e5969d2daa180d2a7f484f4e22b2159498a5339` |
| `governance-and-local-tooling.tar.gz` | Current PAR governance files and local skill mirrors only | See `SHA256SUMS` | See `SHA256SUMS` |

`SHA256SUMS` is the sibling checksum ledger. The governance archive checksum
is deliberately kept there rather than embedded inside a report that the
archive itself contains.

Validation results:

- both bundles passed `git bundle verify` and report complete history;
- the outer bundle exposes 17 refs, including hidden Codex refs and both
  protection tags;
- the nested bundle exposes 11 refs, including `refs/stash`,
  `m1-ready-20260609`, and both nested protection tags;
- both full Git tarballs passed `gzip -t` and archive listing checks;
- recovery directory permissions are owner-only.

These artifacts are local recovery evidence, not a replacement for an
approved off-device backup. No artifact was uploaded.

## 4. Candidate Materialization

The tag was materialized with `git archive` into an ignored temporary path,
without checking it out over the active worktree:

```text
/Users/mac/Downloads/WeKnora-main/tmp/par-p0-01-validation/e7b258c-20260714
```

The reproducible `candidate.tar` is 49,356,800 bytes with SHA-256:

```text
4637b8194adc150214c0a3c9749da46b29d236058747f3bf853cfad9347f23fa
```

The current PAR Spec, baseline report, harness report, checker, and paired
skills were overlaid only into the temporary validation copy for governance
checking. They were not added to the frozen product commit or staged.

## 5. Work Preservation Classification

| Current work category | Preservation proof | Action in this task |
| --- | --- | --- |
| PA and WNID product files shown dirty by the outer repo | Nested tracked tree is clean and equals `e7b258c:pa-ai-workbench` exactly | Frozen in coherent tag and both Git recovery sets |
| Native WNID patch | Present in the same `e7b258c` root tree | Frozen in coherent tag and outer recovery set |
| Nested post-`1b183e3` commit chain | Reachable from nested `e3402c7` | Nested protection tag, bundle, and full `.git` snapshot |
| Nested stash | `a4231cb...` remains at `refs/stash` | Independent protection tag, bundle, and full `.git` snapshot |
| Current PAR governance files | Not part of `e7b258c` | Preserved in the governance/local-tooling archive and active worktree |
| `.agents` local skill mirror | Local governance asset | Preserved in the governance/local-tooling archive and active worktree |
| Personal `docs/resume_project` materials | Nested tracked tree and coherent candidate; content not inspected | Left in place; no publication, move, or deletion decision inferred |
| `.env`, password marker, DB, uploads, logs, output, and other private/runtime data | Path-level classification in `PAR-0-02` | Left in place; contents not read or copied into governance archive |
| Dependency/build caches | Regenerable local state | Left in place and excluded from recovery governance archive |

No private environment file, credential value, database, upload, log, output,
raw document, vector, provider payload, or runtime cache is included in the
governance archive.

## 6. Baseline Validation

All commands below ran against the separately materialized candidate, not the
hybrid current worktree.

| Check | Result |
| --- | --- |
| Candidate commit/tree and PA subtree identity | PASS |
| Python `compileall` for PA backend, Agent, and Knowledge Engine | PASS |
| WNID final acceptance checker | PASS: 17/17 tasks, final ready |
| Frontend TypeScript check and Vite production build | PASS: 1,589 modules transformed |
| Docker Compose config with `.env.example` and an empty temporary `.env` placeholder | PASS |
| Go tests for `internal/agent/...`, `internal/application/service`, `internal/handler/...`, and `internal/mcp/...` using Go 1.26.0 | PASS |
| PAR checker governance mode after temporary governance overlay | PASS |
| PAR checker final mode | Expected FAIL: repository relocation has not started |

One diagnostic wildcard run also included
`internal/application/service/file` and failed
`TestOssEnsureBucket_CreateFails`. That test calls the public Aliyun OSS
endpoint with a fixed bucket name and expects invalid credentials to always
produce an error; it returned no error in this environment. The package is not
part of the native WNID delta. The scoped changed-package suite above passed,
so this environment-sensitive diagnostic is recorded but does not invalidate
the coherent baseline freeze.

Live PA/WeKnora services and browser workflows were not restarted in this Git
freeze task. Their existing WNID evidence is preserved in the candidate; full
new-path live and browser validation remains assigned to `PAR-P4-02`.

## 7. Recovery Procedure

Use a separate empty directory for recovery. Do not extract a full Git snapshot
over either active repository.

Portable history can be inspected by cloning the corresponding bundle:

```bash
git clone outer-all-refs.bundle restored-outer
git clone nested-all-refs.bundle restored-nested
```

The coherent source can be reproduced from the outer clone with:

```bash
git archive --format=tar --output=candidate.tar par-p0-01-coherent-baseline-20260714
```

The full `.git` tarballs are last-resort local metadata recovery copies. Their
use must occur against a copied worktree after checksum verification.

## 8. Decision and Next Gate

`PAR-P0-01` is complete: coherent product/runtime content has a stable
recoverable ref, both histories and hidden work have verified recovery
artifacts, all current work categories are classified, and the scoped baseline
suite passes.

The next task is `PAR-P0-02`. It may establish one canonical Git root and import
the nested history into an unambiguous namespace. Removing or relocating
`pa-ai-workbench/.git` still requires a separate explicit user approval after
that reachability plan is reviewed. This report does not grant that approval.
