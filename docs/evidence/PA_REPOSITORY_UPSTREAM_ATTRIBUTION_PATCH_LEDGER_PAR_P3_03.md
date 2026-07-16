# PA Repository Upstream Attribution and Patch Ledger — PAR-P3-03

## Outcome

`PAR-P3-03` is complete. The PA-first repository now has a root license
boundary, a root third-party notice index, a reproducible WeKnora provenance
record, and an exact controlled native exception ledger. The record explicitly
distinguishes the official version tag, the reconstructed upstream source
anchor, the local root import, the coherent PA/native baseline, and later
path-only PAR relocations.

No PA or WeKnora product behavior, runtime data, Git history, branch, remote,
or running service was changed. No commit, push, merge, service stop, service
restart, or service rebuild was performed.

## Scope and protected boundaries

This task changed attribution/governance material only:

- added root `LICENSE` without inventing a public license grant for PA-owned
  code;
- added `THIRD_PARTY_NOTICES.md` as the repository attribution index;
- normalized 79 inherited line-end whitespace findings and the missing EOF
  newline in `platform/weknora/LICENSE`; a before/after normalized SHA-256
  comparison proves that no license word, punctuation, or paragraph changed;
- finalized `platform/weknora/UPSTREAM.md` and
  `platform/weknora/PA_PATCHES.md`;
- linked the attribution boundary from root `README.md` and `ARCHITECTURE.md`;
- extended the PAR checker with deterministic attribution and ledger gates;
- removed the obsolete `pa-ai-workbench/NOTICE.md` after its valid attribution
  content was superseded. That notice incorrectly described PA as a nested,
  reference-only product and contradicted the controlled native source model.

Real `.env` files, credentials, databases, uploads, logs, output, caches,
vectors, raw documents, and protected personal material were not read, moved,
deleted, or staged. `pa-ai-workbench/docs/resume_project` remains present,
ignored, and unread. P4 static/build, live, and clean-clone acceptance were not
started.

## Verified provenance model

| Layer | Verified identity | Meaning |
| --- | --- | --- |
| Official repository | `https://github.com/Tencent/WeKnora` | Tencent upstream identity |
| Imported version marker | `0.6.0` | Value retained in native `VERSION`; not an exact tree claim |
| Official `v0.6.0` tag | `b0094ff47917b5abece91acff4c7e16710368f2c` | Verified official tag ref |
| Reconstructed source anchor | `482686d17ee89aefea54cf05bf843c04d152db27` | Unique minimum-difference official candidate |
| Local native import | `42a6f0ac810dd04a64a6b0999b06554ac76a5e0b` | Root commit containing the imported source plus PA changes |
| Coherent PA/native baseline | `e7b258c61d56bd44ce477ef29cf761d8ab07cdfc` | Preserved controlled baseline before PAR relocation |

The current lineage does not retain an upstream parent for the local import.
An official clone was therefore created only under `/tmp` and was not added as
a repository remote. All 358 commits reachable from official fetched refs
between 2026-05-20 and the local import timestamp were compared using Git path
and blob identities.

Results:

- the local import differs from the official `v0.6.0` tag in 520 paths;
- `482686d...` is the unique minimum-difference candidate at 25 paths;
- the next candidate, `959eba2...`, differs in 26 paths;
- after six unmistakable PA bootstrap document/script paths are excluded, the
  import-time native difference from `482686d...` is 19 paths;
- therefore `482686d...` is recorded as a reconstructed anchor, not falsely
  described as an exact imported tree.

This resolves the upstream commit/version contract honestly: the official
version-tag commit and the best reproducible source anchor are both recorded,
while the missing original importer selection is disclosed instead of guessed.

## License and notice boundary

- Root `LICENSE` states that the internal PA code receives no public license
  grant unless a component says otherwise.
- `platform/weknora/LICENSE` remains the authoritative Tencent WeKnora MIT and
  bundled third-party license text. Only line-end whitespace/EOF normalization
  was applied so the staged repository passes the whitespace gate.
- `platform/weknora/mcp-server/LICENSE` remains the authoritative standalone
  MCP server MIT text.
- Root `THIRD_PARTY_NOTICES.md` indexes both license files, the official
  repository/version tag, reconstructed anchor, local import, coherent
  baseline, provenance record, and patch ledger.
- Dependency manifests/lockfiles remain authoritative package inventories;
  this task does not claim a new legal audit or release SBOM.

## Native exception inventory

The final ledger contains two exact and independently verified sets:

| Set | Count | Comparison |
| --- | ---: | --- |
| Complete controlled native exception inventory | 50 | reconstructed anchor `482686d...` to coherent baseline `e7b258c...`, excluding seven PA bootstrap artifacts outside native ownership |
| Import-to-coherent WNID subset | 35 | local import `42a6f0a...` to coherent baseline `e7b258c...` |

The 50-path set covers AgentQA/ReACT/evidence, knowledge/Wiki/chunk/Skills,
MCP/SSRF/prompts, Web Search/data sources, model/rerank, and native
configuration/runtime boundaries. The 35-path subset preserves the exact
post-import WNID delta. An audit loaded the checker constants and compared both
sets to Git-generated manifests; both set-equality assertions passed.

Later structural mappings are recorded separately. In particular, original
native `docker-compose.yml` is represented by root
`infra/compose/weknora.yaml` and the root `compose.yaml` product entry. These
PAR path changes are not relabeled as native behavior changes.

## Checker contract

`scripts/validation/check_pa_repository_reorganization.py` now requires:

- root `LICENSE` plus `THIRD_PARTY_NOTICES.md`;
- the upstream repository, version, official tag commit, reconstructed anchor,
  local import, and coherent baseline markers;
- explicit non-tree-equality reconstruction language and comparison counts;
- exact 50-path and 35-path ledger sets;
- license links and the canonical Compose relocation marker.

The existing `--root`, `--self-test`, `--json`, governance, and `--final`
contracts and exit-code semantics remain intact. The self-test positive fixture
contains a complete attribution contract; the negative fixture proves the new
`attribution_contract` final gate rejects incomplete records.

## Validation evidence

| Check | Result |
| --- | --- |
| Checker no-cache compile | PASS |
| Checker `--self-test` | PASS; positive and all negative gates |
| Checker governance, JSON, and explicit `--root` | PASS |
| Root `make validate` | PASS |
| Shell syntax through root validation | PASS |
| Python no-cache syntax validation | PASS, 278 files |
| Root backend discovery | PASS, 3/3 |
| PA Web TypeScript/Vite | PASS, 1,589 modules; output under `/tmp` |
| WNID final checker | PASS, 17/17 and final ready |
| WNFC final checker | PASS, 14/14 and final ready |
| WNX acceptance | PASS, 30 reports |
| Deployment readiness | PASS, static mode |
| Official-ref/provenance comparison | PASS, 358 candidates; unique 25-path minimum |
| 50-path controlled ledger equality | PASS |
| 35-path import-to-coherent equality | PASS |
| Task Markdown relative links | PASS, 45 links |
| PAR Skill quick validation and mirror comparison | PASS |
| Repository-wide staged `git diff --check` | PASS after verified whitespace-only normalization of the imported WeKnora license |
| Task-file sensitive-pattern scan | PASS, 11 files |
| One active Git root and canonical origin | PASS |
| Protected personal boundary | PASS, present and ignored without reading contents |
| Read-only Docker status | PASS, existing `weknora-main` remains `running(5)` |

After the task files are precisely staged, PAR `--final` is expected to fail
only on the P4 task/progress rows, final P4 evidence, and the still-missing
`tests/acceptance` target. An attribution or legacy product-tree blocker is not
an acceptable expected failure.

## Validation limits and residual risk

- The host has no Go CLI and no Helm CLI. This task does not claim current Go,
  Helm, or complete native build PASS; those are `PAR-P4-01` gates.
- The reconstructed anchor is evidence-backed but remains an inference because
  the root import has no upstream parent. Future syncs must preserve the
  quantified distinction and must not relabel the version tag as the source
  commit.
- This task preserves upstream license text and dependency manifests but is not
  a release-specific legal review or generated SBOM.
- Live workflows, browser acceptance, and clean-clone reproducibility remain
  deliberately untested until their P4 tasks.

## Recovery and next task

All changes are ordinary working-tree/index changes and can be recovered from
the existing mixed worktree without rewriting history. The `/tmp` official
clone is disposable comparison evidence only. No destructive rollback command
was used or authorized.

The next task is `PAR-P4-01`: run static, unit, build, path, Compose, Skill,
and sensitive acceptance from the consolidated repository without starting
live or clean-clone acceptance.
