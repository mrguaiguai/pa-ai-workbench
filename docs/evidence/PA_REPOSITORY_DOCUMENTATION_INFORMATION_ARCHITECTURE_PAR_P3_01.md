# PA Repository Documentation Information Architecture — PAR-P3-01

> Date: 2026-07-15
>
> Task: `PAR-P3-01`
>
> Type: docs/runtime hygiene — documentation boundary only
>
> Result: complete

## Scope and safety baseline

This task makes PA AI Workbench the documentation root, separates current
product/stage/evidence material from historical stage records, moves repo-local
Skills to the root, and repairs active references. It does not clean runtime
data, change ignore policy, finalize third-party/upstream notices, start P4
acceptance, or change PA/WeKnora behavior.

The pre-change baseline confirmed one Git root, `HEAD` at `5549670`, canonical
`origin` unchanged, and the preceding mixed index/worktree intact. The
canonical current-stage Spec did not yet exist, so there was no second Spec
with unexplained divergence. Both PAR Skill copies, the bootstrap Spec,
PAR-P2-03 evidence, the Native Expansion architecture, and the WNID final
report were read before editing.

No real `.env`, credential, database, upload, log, output, cache, vector, raw
prompt, or personal-content payload was read or moved.

## Inventory and classification

The bootstrap inventory contained 142 top-level documentation files: 141
Markdown documents plus an empty `.gitkeep`. Two PA root documents and nine
legacy PA/Day-1/Phase specifications also remained outside the documentation
tree. Eighteen repo-local Skill packages remained nested below the legacy PA
tree.

The 141 bootstrap Markdown documents were classified before moving:

| Destination | Count | Classification |
| --- | ---: | --- |
| root product/architecture | 1 | former placeholder architecture, rewritten as current root architecture |
| `docs/product` | 1 | current supporting terminology reference |
| `docs/architecture` | 2 | native expansion architecture and RAG source map |
| `docs/operations` | 1 | active deployment-readiness runbook |
| `docs/stages/current` | 1 | canonical PAR Spec |
| `docs/evidence` | 9 | completed current PAR task evidence |
| `docs/archive/legacy-product` | 1 | early demo document |
| `docs/archive/phase3` | 23 | completed Phase 3 records |
| `docs/archive/phase4` | 7 | completed Phase 4 records |
| `docs/archive/phase5` | 10 | completed Phase 5 records |
| `docs/archive/weknora-first` | 15 | completed WeKnora-first sprint records |
| `docs/archive/wnx` | 30 | completed Native Expansion records |
| `docs/archive/wnfc` | 23 | completed Native Full Completion records |
| `docs/archive/wnid` | 17 | completed Intelligent Dialogue records |

The two former PA root documents became root `README.md` and
`PRODUCT_SPEC.md`. The additional nine v0.1–v0.5, Day-1, and developer specs
were preserved under `docs/archive/legacy-product`; none were deleted or
rewritten as current product truth.

## Canonical documentation boundary

The repository now has one PA-first documentation entry:

- root `README.md`: product identity, root layout, commands, documentation, and
  safety entry;
- root `PRODUCT_SPEC.md`: current workflows, ownership, evidence, mutation,
  delivery, and non-goal contracts;
- root `ARCHITECTURE.md`: PA/WeKnora system boundary, repository ownership,
  runtime/data flow, evidence, and delivery architecture;
- `docs/README.md`: current-versus-archive information architecture;
- `docs/product`, `docs/architecture`, `docs/operations`;
- `docs/stages/current` for the active Spec;
- `docs/evidence` for current PAR evidence;
- `docs/handoff` with an explicit no-preclaimed-P4-PASS boundary;
- `docs/archive/<stage>` for completed and superseded records.

The current canonical tree contains 162 checked Markdown files when the three
root documents are included. Historical files retain their original claims;
their PASS wording is not represented as current-run evidence.

## Skills and active callers

All 18 repo-local Skills moved from the nested legacy location to root
`.github/skills`. The PAR, WeKnora-first, WNX, WNFC, and WNID Skill pairs were
updated with portable root paths and are byte-identical to their `.agents`
mirrors. Legacy phase Skills now point to archived specifications and current
`apps`, `packages`, and `scripts` locations rather than removed product paths.
The `.agents` tree is intentionally ignored by repository policy, so its local
mirrors were validated and compared but were not force-added to the Git index;
the canonical root `.github/skills` packages are tracked.

The PAR checker now resolves only canonical Spec, evidence, and root Skill
locations. Historical WNX/WNFC/WNID and Phase checkers resolve their documents
under the appropriate archive directory. PA API path constants expose root
`docs` and `scripts` while retaining source-compatible constant names.
Workflows, product behavior, API contracts, and runtime configuration were not
changed.

The final `apps/docs` compatibility link was removed after active callers
migrated. Removing the link did not modify its target. No documentation shim
remains; the six independently owned PAR-P2-02 infrastructure links are
unchanged.

## Personal and portfolio material decision

The explicit disposition for the protected `resume_project` directory is:

1. retain it in its existing legacy location;
2. do not expose it through root `docs` or `apps/docs`;
3. do not read, stage, publish, move, archive, or delete its contents;
4. require a later explicit user-selected archive/export destination before
   any physical move.

This is a keep-in-place decision, not an implicit publication or cleanup
decision. Existence was verified without reading the material.

## Validation evidence

### Documentation and path integrity

| Check | Result |
| --- | --- |
| Canonical root identity files and target directories | PASS |
| Bootstrap tracked Markdown remaining | PASS, zero |
| Personal-material existence | PASS, preserved in place |
| Markdown relative-link resolver | PASS, 162 files and zero broken links |
| Active legacy product/docs/Skill path scan | PASS; only the PAR checker's intentional detection marker remains |
| Root repo-local Skills with `quick_validate.py` | PASS, 18/18 |
| Five current repo-local/`.agents` Skill pairs | PASS, byte-identical |
| High-confidence private-key/token scan | PASS, zero matches |
| Placeholder scan over current root/docs/PAR artifacts | PASS, zero matches |
| Staged and unstaged `git diff --check` | PASS |

### Checker and product regression

| Check | Result |
| --- | --- |
| Root `make validate` | PASS |
| Shell syntax and no-cache Python compile | PASS, 21 shell and 278 Python files |
| Root backend discovery | PASS, 3/3 |
| PA Web TypeScript/Vite build | PASS, 1,589 modules; output under `/tmp` |
| PAR governance, JSON, self-test, and cross-cwd `--root` | PASS |
| WNID final checker | PASS, 17/17 and final ready |
| WNFC checker | PASS, 14/14 and final ready |
| WNX acceptance checker | PASS, 30 reports resolved from new paths |
| Deployment-readiness static checker | PASS |
| Phase 5 report-safety self-test | PASS |
| Phase 3 intranet and pilot-document smokes | PASS |

The historical Phase 3 aggregate checker is not claimed as PASS. It now finds
its archived Spec/runbooks, but its old Git-safety rule treats the current PAR
rename of example env and fixture files as sensitive, and its old product UI
term assertions no longer describe the current interface. Those are
historical-checker limitations, not missing P3-01 paths; product behavior was
not changed to satisfy stale assertions.

After path migration, PAR `--final` no longer reports
`canonical_skill_missing`, `canonical_spec_missing`, `root_product_identity`,
`stale_skill_path`, or `old_canonical_reference`. Its expected remaining codes
are `incomplete_progress_evidence`, `incomplete_task_board`,
`legacy_product_tree_present`, `missing_final_evidence`, and
`missing_target_boundaries`. They belong to PAR-P3-02, PAR-P3-03, and P4.

### Service and repository safety

- One active Git root and the canonical origin remain unchanged.
- Read-only Docker status still shows the pre-existing `weknora-main` project
  running five containers from the historical Compose path.
- No service was installed, started, stopped, restarted, rebuilt, or migrated.
- The mixed staged/untracked worktree, ignored runtime state, and protected
  personal material remain preserved.
- No commit, push, merge, rebase, or history rewrite was performed.

## Recovery and residual risk

The move is uncommitted. Tracked `git mv` records, the classification table,
root identity files, zero-broken-link proof, and active-path scans provide
recovery evidence. Any approved reversal can move individual paths back with
`git mv`; destructive reset or checkout is unnecessary.

Residual risks are explicitly deferred:

1. The physical legacy product/runtime tree remains because runtime and
   ignored-data hygiene belongs to PAR-P3-02.
2. `THIRD_PARTY_NOTICES.md`, upstream attribution, and native patch-ledger
   finalization belong to PAR-P3-03.
3. `tests/acceptance`, final evidence, live workflows, and clean-clone handoff
   belong to P4.
4. The protected personal directory remains in place until the user chooses a
   destination.

The next task is `PAR-P3-02`.
