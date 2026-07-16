# PAR-P0-02 Canonical Git Root Consolidation

> Date: 2026-07-14
>
> Task: `PAR-P0-02`
>
> Status: `[x]` complete after explicit user approval
>
> Evidence type: `git-integrity + clean-recovery + one-root`

## 1. Current Decision

The history and physical-root consolidation are complete. Every named
nested ref, the nested stash, the complete post-`1b183e3` PA commit chain, and
the nested repository's only dangling commit are now reachable from the outer
Git object database under a dedicated archive namespace.

After reviewing the recovery evidence, the user explicitly approved the exact
nested Git relocation and local-path remote removal on 2026-07-14. The active
checkout now has exactly one Git root:

```text
/Users/mac/Downloads/WeKnora-main/.git
```

The former nested Git metadata was relocated intact, not deleted, to:

```text
/Users/mac/Downloads/WeKnora-main/tmp/par-p0-02-recovery/20260714/nested-git-dir-live-preserved
```

The outer repository is now the only active owner of the full checkout.

## 2. Canonical Root Decision

The proposed canonical root is:

```text
/Users/mac/Downloads/WeKnora-main/.git
```

Reasons:

1. It owns the complete WeKnora native runtime plus the PA product subtree.
2. `par-p0-01-coherent-baseline-20260714` provides one coherent PA plus native
   WNID content ref.
3. The nested PA history is now separately reachable inside this object
   database without merging or rewriting either history.
4. Its `origin` already points to the PA AI Workbench GitHub repository.

No canonical branch was switched or rewritten in this task. Outer `main`
remains at `5549670`; the coherent source remains protected at `e7b258c`.

## 3. Imported Nested Namespace

The local-only import used an additive fetch from the nested filesystem path to:

```text
refs/archive/pa-nested/20260714/*
```

| Imported role | Outer archive ref | Object |
| --- | --- | --- |
| Nested main | `heads/main` | `36ea9ca30caa5801c3722d23fe3412db80636f02` |
| Nested native baseline | `heads/pa-native-baseline-20260622` | `36ea9ca30caa5801c3722d23fe3412db80636f02` |
| Nested PA head | `heads/weknora-first-mvp` | `e3402c7ac0667a1a3c8282b668997693b9a4d170` |
| Nested origin snapshots | `remotes/origin/*` | Exact source ref values |
| Nested stash | `stash` | `a4231cb53cd25ae596a221b110e95962bb7ca393` |
| Nested milestone tag | `tags/m1-ready-20260609` | `2103ff70367d38b3bfe5c03190f8d76e3dda7a16` |
| P0-01 nested protection tags | `tags/par-p0-01-nested-*` | Exact source ref values |
| Recovered dangling commit | `recovered-unreachable-commits/47a9f99...` | `47a9f99b76d2868d63a8bb2b9439ee83806c07e3` |

The recovered commit has subject `chore: initialize PA AI workbench spec` and
was not attached to product history. It is preserved as recovery evidence, not
merged into the canonical lineage. Remaining dangling blobs are preserved in
the P0-01 full nested `.git` snapshot; they were not promoted into invented
history.

The four nested commits after `1b183e3` are all ancestors of the imported head:

```text
c791ed1  feat: complete native full completion sync
b8a9e82  fix: refresh document processing status
d02519d  feat: complete native intelligent dialogue stage
e3402c7  feat: streamline intelligent dialogue experience
```

The imported nested head tree remains exactly equal to the coherent outer PA
subtree:

```text
e7b258c:pa-ai-workbench                                      c053ea532aabac1614e10c4f37e2863d46f3fcf1
refs/archive/pa-nested/20260714/heads/weknora-first-mvp^{tree} c053ea532aabac1614e10c4f37e2863d46f3fcf1
```

## 4. Post-Import Recovery Evidence

Recovery directory:

```text
/Users/mac/Downloads/WeKnora-main/tmp/par-p0-02-recovery/20260714
```

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `outer-with-nested-history.bundle` | 24,969,948 bytes | `ac8d8d4e541f99e69eb1fc95a709618ec9755320245200ecb5ec1717334d4158` |
| `outer-with-nested-history-git-dir.tar.gz` | 27,805,438 bytes | `b910691a8c44368c8d43a69b49a48a1a73c30a860b6fb0aa365fe8f32ee5d44a` |
| `governance-progress.tar.gz` | See `SHA256SUMS` | See `SHA256SUMS` |

The bundle passes `git bundle verify`, reports complete history, and exposes 28
refs. Those refs include the coherent tag, outer branches, hidden Codex refs,
all 10 imported named nested refs, and the recovered dangling-commit ref. The
full post-import outer `.git` snapshot passed `gzip -t`.

The P0-01 pre-import outer/nested bundles and full Git snapshots remain intact
and checksum-valid. They provide independent before-and-after recovery points.
The relocated live nested metadata is also owner-only and independently
readable with an explicit `--git-dir` and `--work-tree`.

## 5. One-Root Recovery Proof

The post-import bundle was fetched into an empty temporary Git repository.
That isolated repository then checked out the coherent tag and proved:

- exactly one `.git` directory existed;
- the coherent checkout HEAD was `e7b258c`;
- the nested head, stash, milestone tag, protection refs, and recovered
  dangling commit were readable;
- `HEAD:pa-ai-workbench` equaled the imported nested head tree;
- the working tree was clean in detached validation state.

After validation, its generated `.git` directory was renamed to
`git-dir-preserved-after-validation` so the active workspace inventory still
contains only the two original Git roots. The temporary proof did not alter the
active checkout.

## 6. Remote Roles

Final active configuration is:

| Location | Remote | Final role |
| --- | --- | --- |
| Outer | `origin` | The only active canonical PA product remote; URL unchanged |
| Relocated nested metadata | `origin` | Inactive recovery metadata only; readable through explicit `--git-dir` |
| Outer | WeKnora upstream | Not configured; verified URL and attribution remain assigned to `PAR-P3-03` |

No fetch from GitHub was performed, so local remote-tracking refs are still
snapshots rather than claims about current server state. The outer local-path
remote named `pa-ai-workbench` was removed after approval. The GitHub `origin`
URL and fetch refspec were not changed.

## 7. Preserved User Work

- The active hybrid working tree was not checked out, reset, staged, committed,
  merged, or cleaned.
- Current PAR governance files remain untracked in the active outer worktree
  and are preserved in the P0-02 governance archive.
- The nested stash still exists in the relocated metadata and at the outer
  archive ref.
- Personal materials, private/runtime data, `.env` files, databases, uploads,
  logs, output, dependencies, and caches were neither read nor moved.
- The outer `.git` remains in place; the nested `.git` was relocated intact to
  the approved recovery path and was not deleted.

## 8. Approved Completion Action

After the user explicitly approved the exact boundary, this task:

1. relocated—not deleted—`pa-ai-workbench/.git` to the owner-only ignored path
   `tmp/par-p0-02-recovery/20260714/nested-git-dir-live-preserved`;
2. removed the outer local-path remote named `pa-ai-workbench`, leaving `origin`
   as the only canonical product remote;
3. verified exactly one active `.git`, all archive refs, coherent tree equality,
   relocated stash/history readability, current user-work inventory, and PAR
   governance mode.

All checks passed. This action changed Git ownership and local remote
configuration only. It did not change source files, delete metadata, fetch or
push, stage work, create a commit, merge histories, or switch a branch.

## 9. Decision and Next Task

`PAR-P0-02` is complete. The active checkout has one canonical Git root, one
active canonical product remote, coherent product/runtime content, and outer
archive reachability for the complete named nested history and stash. Both
pre- and post-consolidation recovery sets remain available.

The next task is `PAR-P1-01`: relocate the controlled WeKnora platform under
`platform/weknora` as a pure ownership-boundary move.
