# PA Repository Static, Unit, and Build Acceptance — PAR-P4-01

## Outcome

`PAR-P4-01` is complete. The consolidated PA-first repository passes its
static repository contracts, root command validation, PA backend tests,
Python distribution builds, PA Web type/build checks, controlled native Go
tests and vet, broad native package tests, native server/client/CLI builds,
Compose rendering, Docker build-context checks, workflow parsing, Helm static
checks, Skill validation, path scans, and sensitive-data gates.

This is static, unit, and build evidence only. It is not live-workflow,
browser, or clean-clone evidence. No existing service was started, stopped,
restarted, rebuilt, or replaced. No commit, push, merge, history rewrite, or
branch operation was performed.

## Scope and protected boundaries

The task adds one deterministic repository acceptance suite and exposes it
through the root command surface:

- `tests/acceptance/test_repository_static_contract.py` checks PA-first target
  boundaries, root workspaces and commands, the six controlled compatibility
  links, workflow paths, all Dockerfile host-side `COPY` sources, attribution
  markers, and absence of the retired product-root path;
- root `Makefile` adds `validate-static-acceptance` and includes it in
  `make validate`;
- this report records the exact validation scope and limitations;
- the PAR task board and progress log advance only `PAR-P4-01`.

Real `.env` files, credentials, databases, uploads, logs, output, caches,
vectors, raw documents, and protected personal material were not read, moved,
deleted, or staged. `pa-ai-workbench/docs/resume_project` remains present and
ignored without content inspection. Existing mixed-index work from earlier PAR
tasks remains preserved.

## Canonical acceptance command

Run the repository-owned static contract from the repository root:

```bash
make validate-static-acceptance
```

The aggregate root command now includes the same gate:

```bash
make validate
```

The acceptance suite is deliberately read-only. Its seven tests validate:

1. PA-first apps, packages, platform, infrastructure, scripts, docs, and test
   boundaries;
2. root Python/Node workspace files and root Make targets;
3. the six bounded compatibility links and their canonical destinations;
4. canonical paths in all five GitHub workflows;
5. all 33 Dockerfile host-side `COPY` sources against their declared contexts;
6. root license, third-party notice, upstream, and PA patch-ledger markers;
7. zero tracked or unignored files below the retired product-root directory.

## PA static, unit, and build results

| Gate | Result |
| --- | --- |
| Root `make validate` | PASS |
| Shell syntax through the root command surface | PASS |
| Python no-cache syntax validation | PASS, 279 files |
| Repository static-contract suite | PASS, 7/7 |
| Root backend unit discovery | PASS, 3/3 |
| PA API wheel build and isolated import | PASS |
| PA Agent Runtime wheel build and isolated import | PASS |
| PA Knowledge Engine wheel build and isolated import | PASS |
| PA Web TypeScript check | PASS |
| PA Web Vite production build | PASS, 1,589 modules |

The three Python distributions were built with `pip wheel --no-deps
--no-build-isolation` because the host does not provide the optional `build`
module. Each wheel was installed into an isolated `/tmp` target, and the
`app`, `agent`, and `knowledge_engine` packages were resolved from those
isolated targets. No global or project environment was modified. PA Web output
was written below `/tmp`, not the working tree.

The host's default shell `PATH` does not expose a Node binary. The first
aggregate attempt therefore stopped at the Web target with `env: node: No such
file or directory` after its preceding gates passed. Re-running with the
configured bundled Node runtime on `PATH` completed the aggregate command. A
checkout running the Web gates requires Node on `PATH`; this is an explicit
toolchain prerequisite, not a product or test PASS concealed by the report.

The wheel builds created package-specific `build/` and `*.egg-info/`
intermediates before placing the wheels in `/tmp`. Those six precisely
identified generated directories were removed after validation; pre-existing
ignored caches and all user/runtime paths were left untouched. The final
working-tree scan has no wheel-build residue.

## Native Go acceptance

The host still has no Go CLI. Native validation therefore used the locally
available `golang:1.26.0` image with the repository mounted read-only and all
build/module caches below `/tmp/par-p4-01-go-cache`. This is real Go compiler,
test, vet, and build execution; it is not a simulated PASS.

| Gate | Result |
| --- | --- |
| Container toolchain identity | PASS, `go1.26.0 linux/arm64` |
| Controlled root packages | PASS, 11 packages |
| Broad root package suite | PASS, 78/81 package paths |
| Controlled root `go vet` | PASS |
| Native server build with SQLite headers | PASS |
| `client` module `go test ./...` | PASS |
| `client` module `go vet ./...` | PASS |
| `cli` module `go test ./...` | PASS |
| `cli` module `go vet ./...` | PASS |
| `cli` binary build to `/tmp` | PASS |

The controlled suite covered agent, approval, memory, skills, token, tools,
application service, handler, handler DTO/session, and MCP packages. The broad
suite installed `libsqlite3-dev` only inside an ephemeral build container and
passed every root module package except three explicitly classified domains.
The native server binary was built separately to `/tmp`; no repository artifact
or running image was changed.

For transparency, an unfiltered diagnostic `go test ./...` was also run and is
not reported as PASS. Its remaining failures are:

- `docreader/client` integration tests require a live DocReader endpoint at
  `localhost:50051`;
- `internal/application/service/file` retains the previously documented public
  Aliyun OSS invalid-credential/environment-sensitive test assumption;
- `internal/application/repository/retriever/doris` retains three upstream SQL
  expectation mismatches outside the 50-path PA controlled native exception
  ledger.

The initial plain Go image also lacked `sqlite3.h`; installing the header only
inside a disposable container proved the server and the remaining SQLite
packages build. The three exclusions above are external-service or upstream
residuals, not hidden relocation regressions. They remain explicit risk for
later product/upstream work and must not be converted into an unconditional
full-suite claim.

## Frontend, Compose, Docker, workflow, and Helm results

| Gate | Result |
| --- | --- |
| PA Web TypeScript/Vite build | PASS |
| Native frontend Buildx production build | PASS, 6,083 modules |
| Root `compose.yaml`, all profiles | PASS |
| Canonical WeKnora Compose render | PASS |
| Canonical WeKnora development Compose render | PASS |
| Controlled compatibility Compose render | PASS |
| Seven Dockerfiles, BuildKit `--check` | PASS |
| Docker host-side `COPY` context/source contract | PASS, 33/33 |
| Five GitHub workflow YAML parses | PASS |
| Workflow canonical-script/path assertions | PASS |
| Helm chart YAML and template delimiter checks | PASS, 16 files |

The native frontend used Buildx `--output type=cacheonly`; the production Vite
build completed and no image was loaded, tagged, or attached to a service. It
reported dependency-audit and large-chunk warnings but no build error.

Compose validation used example environment data and `--no-env-resolution`.
No real environment file was inspected and no service was started. Dockerfile
checks validated the PA API, PA Web, native app, DocReader, sandbox, native
frontend, and MCP images. The host has no Helm CLI, so this report claims
static chart/YAML/template validation, not `helm lint`.

## Product and governance regression

| Check | Result |
| --- | --- |
| WNID final acceptance | PASS, 17/17 and final ready |
| WNFC final acceptance | PASS, 14.00/14 and final ready |
| WNX acceptance | PASS, 30 reports and 12.00/15 target |
| Deployment readiness | PASS, static mode |
| PAR checker no-cache compile | PASS |
| PAR checker self-test | PASS |
| PAR governance, JSON, and explicit `--root` | PASS |
| All repository and `.agents` Skill quick validations | PASS |
| Five shared Skill mirror comparisons | PASS |
| One active Git root and canonical origin | PASS |
| Read-only Docker status | PASS, existing `weknora-main` remains `running(5)` |

The PAR `--final` gate remains expected to fail only for the unfinished
`PAR-P4-02` and `PAR-P4-03` task/progress/evidence contracts. A target-boundary,
P4-01-evidence, old-path, attribution, or static/build blocker is not an
acceptable expected failure after this task.

## Path, safety, and recovery evidence

- The active repository contains exactly one `.git` directory.
- `origin` remains
  `git@github.com:wjr1314lxj-star/pa-ai-workbench.git` for fetch and push.
- The retired product-root path has zero tracked and zero unignored files.
- The six compatibility links resolve to canonical infrastructure paths and no
  new compatibility shim was added.
- Old-path, Python root inference, fixed working-directory, Compose/Dockerfile,
  workflow, and command-path assertions pass through the acceptance suite and
  PAR checker.
- Task-file and staged-diff sensitive-pattern scans pass without reading real
  secret or user-data paths.
- `git diff --check` passes for both working-tree and staged changes.
- Existing staged PAR migrations and ignored/untracked user/runtime work remain
  preserved; only the P4-01 files are added to the existing index.

All P4-01 changes are ordinary file/index changes and can be recovered from the
existing working tree without destructive Git operations. Disposable wheels,
install targets, Go caches, server/CLI binaries, Web output, and container build
caches were kept outside the repository. No rollback, cleanup, or runtime
mutation was authorized or performed.

## Validation limits and residual risk

- Live API/browser workflows, real service mutation, and confirmation/audit/
  history/citation behavior are deferred to `PAR-P4-02`.
- Clean-clone setup, build, start, status, workflow, browser, and handoff proof
  are deferred to `PAR-P4-03`.
- The host lacks Go and Helm CLIs. Go acceptance used a pinned local container;
  Helm acceptance is static only.
- The native dependency audit reports seven dependency advisories and large
  output chunks; neither warning was introduced or remediated by this
  architecture task.
- The three unfiltered native Go test domains documented above require
  external-service fixtures or separate upstream/product repair ownership.

## Next task

The next and only next task is `PAR-P4-02`: perform live workflow acceptance
against the reorganized repository while preserving the existing service and
the confirmation, audit, history, citation, MCP, Web Search, and non-mock
evidence contracts. Clean-clone acceptance remains deferred to `PAR-P4-03`.
