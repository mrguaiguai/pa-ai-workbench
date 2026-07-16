# PA Repository Command Surface Consolidation — PAR-P2-03

> Date: 2026-07-15
>
> Task: `PAR-P2-03`
>
> Type: command/path/build migration
>
> Result: complete

## Scope and safety baseline

This task consolidates developer, operations, release, and validation commands
without changing PA or WeKnora product behavior. It does not perform the P3
documentation, runtime-artifact, or attribution work, and it does not start the
P4 live or clean-clone acceptance tasks.

The required pre-change checks showed:

- one Git root at `/Users/mac/Downloads/WeKnora-main/.git`;
- `HEAD` at `5549670` with the preceding four commits unchanged;
- canonical `origin` unchanged at
  `git@github.com:wjr1314lxj-star/pa-ai-workbench.git`;
- a large mixed index/worktree from the preceding PAR tasks, all preserved;
- no canonical current-stage Spec copy at
  `docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md`, so
  there was no second Spec with unexplained divergence.

Both PAR Skill copies, the bootstrap Spec, PAR-P2-01 and PAR-P2-02 reports,
the WeKnora Native Expansion architecture, and the WNID final report were read
before implementation. No real `.env`, credential, database, upload, log,
output, vector, cache, or personal-content payload was read, moved, or deleted.
`pa-ai-workbench/docs/resume_project` remains present.

## Command inventory and ownership decision

The inventory covered root and child Makefiles, all shell and Python entry
points, `pa-ai-workbench/scripts`, `apps/scripts`, `apps/backend/scripts`,
`apps/pa-api/scripts`, `platform/weknora/scripts`, workflow calls, LaunchAgent
installers, package scripts, root inference, `sys.path`, fixed working
directories, Compose/Docker paths, and documentation references.

The resulting root command implementation contains:

| Owner | Files | Content |
| --- | ---: | --- |
| `scripts/dev` | 5 | PA setup/process control and native development commands |
| `scripts/ops` | 7 | four shell operations plus three MCP/RSS Python operations |
| `scripts/release` | 11 | eight release shell commands, cloud-image units, and its README |
| `scripts/validation` | 142 | 138 Python validators/smokes and four shell validators |

There are 141 Python and 21 shell command files across the four owners. The
following component-internal scripts intentionally remain beside their
components because their location is part of an image, build, Skill, or
example contract rather than the public repository command surface:

- `platform/weknora/scripts/docker-entrypoint.sh`;
- `platform/weknora/frontend/docker-entrypoint.sh`;
- `platform/weknora/docreader/scripts/generate_proto.sh`;
- Skill-local and example scripts under the native platform.

## Canonical root commands

The new root `Makefile` is the PA-first public entry point. `make help` exposes
the stable surface:

- development: `make setup`, `make start`, `make pa-start`, `make pa-stop`,
  `make pa-status`, `make pa-logs`, and native development targets;
- operations: read-only `make status`, `make compose-config`, and explicit
  LaunchAgent install/uninstall targets;
- release: `make release-version`, `make release-images`,
  `make release-lite`, and `make release-mac`;
- validation: `make validate`, `make validate-par`,
  `make validate-par-json`, and `make validate-par-final`.

The default `make validate` path is static/offline: it does not start, stop,
rebuild, or migrate services, disables PA dotenv loading, uses an in-memory
database and temporary upload path, and sends Vite output to `/tmp`.

## Migration map

Tracked moves preserve the existing command content while placing it under an
explicit owner:

- `pa-ai-workbench/scripts/*.sh` moved to `scripts/dev` or `scripts/ops`;
- the former root native setup/start/dev/quick-dev commands moved to
  `scripts/dev`;
- native service and migration commands moved to `scripts/ops`;
- native image/version/package/Homebrew/cloud-image commands moved to
  `scripts/release`;
- 141 PA command Python files moved from `apps/pa-api/scripts`: three
  mutation-capable MCP/RSS helpers to `scripts/ops`, and the remaining 138 to
  `scripts/validation`;
- native environment, Homebrew, service, and manual Agent configuration checks
  moved to `scripts/validation`;
- the PAR checker moved to
  `scripts/validation/check_pa_repository_reorganization.py`.

Callers were migrated in the native Makefile, root GitHub workflows, shell
cross-calls, Python sibling imports, validation subprocesses, deployment
readiness checks, and database migration operator messages. Repository-root
inference now resolves from the new command directories; PA source roots are
`apps/pa-api` and `apps/pa-web`; package roots remain under `packages`; native
Compose and Docker references use the canonical root `infra` paths.

## Compatibility and residual references

No old command shim is retained. Active callers were migrated before removing
the `apps/backend`, `apps/frontend`, and `apps/scripts` aliases. The remaining
`apps/docs` link is documentation-only and belongs to PAR-P3-01. The six
bounded PAR-P2-02 infrastructure links remain under their recorded owner; they
are not command shims.

Old command-path scanning is classified as follows:

- **migrated:** active Makefiles, workflows, Go operator hints, shell and
  Python calls use the root command surface;
- **explicit compatibility:** no command entry; only the independently owned
  infrastructure links and `apps/docs` remain;
- **P3 historical documentation:** prior evidence reports, bootstrap task-card
  history, and `platform/weknora/docs/PA_WORKBENCH_QUICKSTART.md` retain old
  examples until PAR-P3-01 reorganizes documentation;
- **user material:** private/runtime directories and personal documents were
  not inspected or changed; ignored `apps/pa-api/scripts/__pycache__` content
  was not cleaned as part of PAR-P2-03.

## Validation evidence

### Commands, paths, build metadata, and CI

| Check | Result |
| --- | --- |
| Root `Makefile` dry-run for help/setup/start/status/Compose/release/validation | PASS |
| Native Makefile dry-run for dev/status/start/migrate/build/package targets | PASS; all resolve to root `scripts/*` |
| All 21 migrated shell files with `bash -n` | PASS |
| All 141 command Python files compiled with `compile()` and no cache writes | PASS |
| API, packages, scripts, and tests Python compile scan | PASS, 278 files |
| Shell executable-bit check | PASS |
| Canonical import of `app`, `agent`, `knowledge_engine`, and `app.main:app` | PASS |
| Root inference and obsolete active command-path scans | PASS; no unsafe active derivation remains |
| Root and canonical native `docker compose ... config --quiet` | PASS |
| Five root workflow YAML files | PASS; canonical script paths exist |
| LaunchAgent embedded plist parsing and working-directory assertions | PASS, two plists; no install/uninstall/restart performed |
| PA Web `tsc --noEmit` and Vite production build | PASS, 1,589 modules; output in `/tmp/pa-ai-workbench-par-p2-03-web` |

### PAR checker contract

The relocated checker preserves every required mode and exit semantic:

| Check | Result |
| --- | --- |
| No-cache source compile | PASS |
| `--self-test` | PASS; positive final and negative required gates |
| governance mode | PASS; zero governance issues |
| `--json` | PASS; machine-readable result |
| `--root /Users/mac/Downloads/WeKnora-main` from `/tmp` | PASS |
| `--final` | Expected non-zero; only P3/P4 final-state gaps remain |

The P2-03 old-command blocker was removed. Before the task board update the
remaining final codes were `canonical_skill_missing`, `canonical_spec_missing`,
`incomplete_progress_evidence`, `incomplete_task_board`,
`legacy_product_tree_present`, `missing_final_evidence`,
`missing_target_boundaries`, `root_product_identity`, and `stale_skill_path`.
Those are intentionally owned by PAR-P3-01/P3-02/P3-03/P4, not this task.

### Product regression and governance

| Check | Result |
| --- | --- |
| Root backend discovery | PASS, 3/3 |
| `smoke_wiki_l5.py` | PASS |
| `smoke_weknora_wiki_refs_m1.py` | PASS |
| `smoke_agent_evidence_policy_m2.py` | PASS |
| `smoke_rag_debug_params_m2.py` | PASS |
| WNID final acceptance | PASS, 17/17 and final ready |
| Both PAR Skills with `quick_validate.py` | PASS |
| Skill `SKILL.md` and `agents/openai.yaml` mirror comparison | PASS, byte-identical |
| Active Git roots and `origin` | PASS; one root and unchanged canonical remote |
| Read-only Docker status | PASS; pre-existing `weknora-main` still running five containers from the historical Compose path |

Two additional diagnostics are not represented as PASS and did not trigger a
product change: `smoke_retrieval_parameters_m3.py` has an older fixture that
does not handle the current Wiki preflight request, and the localhost-only
`check_weknora_native_agentqa_workflow.py` reached the application but received
HTTP 503. The established command-migration regressions above pass; these
diagnostics remain transparent follow-up risk for P4 rather than reasons to
alter behavior in a path-only task.

Host Go and Helm CLIs remain unavailable. No Go-test or Helm-lint PASS is
claimed. Their final acceptance remains assigned to PAR-P4-01. The existing
Docker project was not stopped, rebuilt, or migrated.

## Recovery, staging, and residual risk

The migration remains uncommitted. Git's staged move/create/delete record,
the before/after map above, command dry-runs, and the canonical-path scans are
the recovery evidence. If reversal is later approved, each listed tracked move
can be reversed individually with `git mv`; no reset, destructive checkout,
rebase, or history rewrite is required.

The mixed worktree remains intentionally mixed. A pre-final-staging status
observation reported 2,280 entries, including 40 untracked entries and all
preceding PAR changes. PAR-P2-03 stages only its root Makefile, command trees,
removed command aliases, repaired callers, this report, and the Spec update.
It does not commit, push, or merge.

Residual risks are bounded to the two transparent diagnostic limitations,
missing host Go/Helm toolchains, historical command examples awaiting
PAR-P3-01, and final clean-clone/live acceptance awaiting P4. The next task is
`PAR-P3-01`.
