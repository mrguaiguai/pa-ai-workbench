# PA Repository Infrastructure Consolidation — PAR-P2-02

Date: 2026-07-15
Status: `[x]` validated complete
Evidence classes: static, build, service-status observation

## Scope and safety boundary

PAR-P2-02 consolidates Compose, Docker, Helm, environment examples, and active
GitHub workflows under the PA-first repository root. It does not relocate the
developer/operations/release command surface (`PAR-P2-03`), reorganize the
documentation tree (`PAR-P3-01`), change runtime-data ownership
(`PAR-P3-02`), or change PA/WeKnora product behavior.

The run began from the single Git root at
`/Users/mac/Downloads/WeKnora-main/.git`. `origin` remained unchanged. The
existing mixed worktree, its untracked files, ignored runtime state, private
environment files, databases, uploads, logs, output, caches, vectors, and
`docs/resume_project` were not read, moved, cleaned, or removed. No commit,
push, merge, rebase, history rewrite, service start, service stop, or service
recreate was performed.

## Pre-move inventory and canonical placement

| Infrastructure | Before PAR-P2-02 | Canonical result |
| --- | ---: | --- |
| Compose definitions | 2 under `platform/weknora` | `infra/compose/weknora.yaml`, `infra/compose/weknora.dev.yaml`, plus root `compose.yaml` |
| Native Dockerfiles | 5 under `platform/weknora/docker` | `infra/docker/weknora/Dockerfile.*` |
| Native Docker support files | supervisord and SearXNG settings | `infra/docker/weknora/supervisord.conf`, `infra/reverse-proxy/searxng/settings.yml` |
| Helm files | 16 under `platform/weknora/helm` | 16 under `infra/helm/weknora` |
| Active workflows | 4 under `platform/weknora/.github/workflows` | 4 under root `.github/workflows`, plus PA image workflow |
| Environment examples | native, PA API, and PA Web examples | `infra/env/compose.env.example`, `pa-api.env.example`, `pa-web.env.example` |

Tracked relocation used `git mv`. Native Dockerfiles remain byte-identical to
their pre-move content. Their Git blob hashes are:

- app: `38e12b06c440ad3196a5c03bc049aca4693ca586`
- docreader: `47934633a37ddbbb4971bb3df514d283cc3d7366`
- sandbox: `971a8b2a652613e4e724da4cf7125f8cec85ab0d`
- frontend: `6a958a3f79c9b1f9010972dd08e8899dbdcf1380`
- MCP: `5b76a614df918d0b428197ad8b6991556ff40496`

The unmodified release workflow also retains blob
`527d4b90292b0dec380ac123be7f2b05b1ea312d`. Workflows, Compose definitions,
and the three environment examples received only the path, root-product, and
build-context changes required by this consolidation.

## Root infrastructure contract

Root `compose.yaml` includes the canonical WeKnora Compose definition and adds
the PA API and PA Web services. The PA API reaches the native service through
`http://app:8080`; both PA services join the native network and have explicit
health checks. PA persistent state uses the `pa-data` named volume. The real
root `.env` is optional and was not read; validation used
`infra/env/compose.env.example`.

The root Docker context is deny-by-default through `.dockerignore`. Only the
three installable PA Python projects, PA Web build inputs, and the Nginx
configuration are admitted. The PA API and PA Web Dockerfiles live at
`infra/docker/pa-api` and `infra/docker/pa-web`. The workflow
`.github/workflows/pa-images.yml` builds both definitions without pushing.

Native Compose build contexts remain rooted at the controlled source under
`platform/weknora`; their Dockerfile paths now resolve to
`infra/docker/weknora`. This preserves WeKnora ownership of native RAG,
Document, Wiki, AgentQA, MCP, Web Search, model, parser, vector-store, and data
source capability.

## Compatibility shims

Six relative links preserve existing command/document entry points while
their owning later tasks remain open:

- `platform/weknora/docker-compose.yml` -> `infra/compose/weknora.yaml`
- `platform/weknora/docker-compose.dev.yml` -> `infra/compose/weknora.dev.yaml`
- `platform/weknora/helm` -> `infra/helm/weknora`
- `platform/weknora/.env.example` -> `infra/env/compose.env.example`
- `apps/pa-api/.env.example` -> `infra/env/pa-api.env.example`
- `apps/pa-web/.env.example` -> `infra/env/pa-web.env.example`

No Dockerfile compatibility link is retained: Docker rejects a Dockerfile
symlink that escapes its build context. The native Makefile and image build
script therefore use the canonical Dockerfile path directly. `PAR-P2-03`
owns command-dependent Compose/env links; `PAR-P3-01` owns documentation-only
Helm references.

## Validation evidence

### Infrastructure static/build

- `docker compose ... config --no-env-resolution` passed for root, canonical
  native, canonical native-dev, and legacy native-link entry points.
- Root all-profile rendering exposes the included native services and PA API/
  Web; canonical contexts resolve to `platform/weknora`,
  `platform/weknora/frontend`, `platform/weknora/mcp-server`, or the repository
  root as intended.
- `docker build --check` passed without warnings for all seven Dockerfiles:
  PA API, PA Web, native app, docreader, sandbox, frontend, and MCP.
- A context-aware COPY scan proved 33 host sources exist and remain within
  their selected contexts; 18 cross-stage COPY sources were classified
  separately.
- `make -n` passed for native app/docreader/frontend image targets;
  `bash -n platform/weknora/scripts/build_images.sh` passed.
- All five root workflow YAML files parsed successfully. Native image workflow
  Dockerfile paths and CLI workflow self-trigger paths use the root layout.
- Helm `Chart.yaml` and `values.yaml` parsed as YAML; all 16 Helm files were
  present and every template had balanced Go-template delimiters.
- A local Helm CLI was unavailable. A third-party-container lint was not used
  because mounting the private worktree into an untrusted image would violate
  the repository safety boundary. This is explicitly static Helm evidence,
  not a claimed live install/lint result; full Helm/runtime acceptance remains
  in `PAR-P4-01`/`PAR-P4-02`.
- Old active infrastructure-path scanning found no canonical callers of the
  relocated Compose, Dockerfile, Helm, SearXNG, or nested workflow paths. The
  six documented compatibility links are the intentional residual entries.

### Product regression

- Root backend discovery: 3/3 tests passed.
- Python source compilation using `compile()` without cache writes: 278 files
  passed across PA API, scripts, Agent Runtime, Knowledge Engine, and tests.
- PA Web TypeScript checking and Vite production build passed; build output
  was directed to `/tmp`, not the worktree.
- The native web-search Go package was not re-tested because no host Go CLI is
  installed. PAR-P2-02 changed only its infrastructure-path comment; the
  native app Dockerfile definition and context passed BuildKit validation.
  This is not represented as Go-test PASS; native Go acceptance remains a
  required `PAR-P4-01` gate.

### Governance and safety

- PAR checker self-test passed both positive-final and negative-required-gate
  fixtures.
- PAR checker governance mode passed with zero governance issues.
- Both PAR Skill copies passed the canonical Skill validator; `SKILL.md` and
  `agents/openai.yaml` mirrors are byte-identical.
- Six compatibility links resolve successfully.
- `git diff --check` passed.
- A targeted scan across 36 task infrastructure files found no private key,
  GitHub PAT, AWS access key, or live-looking OpenAI key. Existing example-only
  local-development placeholders remain classified as examples, not secrets.
- Read-only Docker service status showed a pre-existing `weknora-main` project
  running five containers from the historical root Compose path. PAR-P2-02 did
  not start, stop, inspect payloads from, or recreate that user-owned service.
- PAR checker `--final` remains expected to fail only on later-stage canonical
  Skill/Spec, command, docs, evidence, product-identity, and unfinished-task
  gates. It must not be interpreted as a PAR-P2-02 failure.

## Recovery evidence and residual risk

The migration is uncommitted. Git rename detection plus the before/after map,
blob hashes, canonical Compose rendering, and resolving compatibility links
provide recovery evidence without modifying Git history. If reversal is ever
approved, the listed moves can be reversed individually with `git mv` after
preserving the mixed worktree; no destructive reset or checkout is required.

Residual risks are deliberately bounded:

1. Helm CLI lint/install was not run locally.
2. Native Go tests were not rerun because the host Go toolchain is absent.
3. The running historical `weknora-main` deployment has not been recreated
   from root `compose.yaml`; live migration belongs to `PAR-P4-02`.
4. Six compatibility links remain until their explicit P2-03/P3-01 owners
   migrate the dependent command/document references.
5. Example environment files retain inherited local-development placeholder
   defaults; production credentials must be supplied only through an ignored
   root `.env` or external secret mechanism.

## Next task

`PAR-P2-03` — consolidate developer, operations, release, and validation
commands. It must consume the canonical infrastructure paths, migrate or
document old command entry points, and leave P3 documentation/runtime-hygiene
work out of scope.
