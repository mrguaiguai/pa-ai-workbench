# PA AI Workbench

PA AI Workbench is an internal productivity product for financial public
affairs teams. It combines a React workspace, a FastAPI application service,
professional workflows, history, citations, and audit with WeKnora knowledge,
RAG, Wiki, AgentQA, tools, MCP, Web Search, model, parser, vector-store, and
connector capabilities.

## Repository layout

```text
apps/pa-web                  React operator workspace
apps/pa-api                  FastAPI application service and business state
packages/agent-runtime       Professional workflow and orchestration package
packages/knowledge-engine    Platform adapter and evidence normalization
platform/weknora             WeKnora knowledge and Agent runtime
infra                        Compose, Docker, Helm, and environment examples
scripts                      development, operations, release, and validation
tests                        repository-level tests and acceptance contracts
docs                         current product docs, evidence, and archives
```

The detailed module responsibilities are in [ARCHITECTURE.md](ARCHITECTURE.md), and the
product contract is in [PRODUCT_SPEC.md](PRODUCT_SPEC.md).

Repository licensing boundaries are recorded in [LICENSE](LICENSE). WeKnora
and dependency attribution is indexed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), with exact provenance and the
integration patch inventory under `platform/weknora/UPSTREAM.md` and
`platform/weknora/PA_PATCHES.md`.

## Root commands

Run commands from the repository root:

```bash
make help
make setup
make start
make status
make validate
make validate-par-final
```

- `make help` lists the supported root command surface.
- `make setup` prepares local dependencies.
- `make start` is an explicit state-changing start command.
- `make status` is read-only.
- `make validate` runs the static/offline command, Python, backend, Web, and
  repository-governance gates. Web output is written to `/tmp`.
- `make validate-clean-clone` exports the exact Git index to a temporary seed
  repository, clones it, and reproduces setup, build, isolated start/status,
  live workflow/browser, and final governance acceptance.
- `make validate-par-final` is the final PAR evidence gate.

Direct implementations are grouped under `scripts/dev`, `scripts/ops`,
`scripts/release`, and `scripts/validation`. Read
[scripts/README.md](scripts/README.md) before invoking mutation-capable
operations, migrations, release commands, or live checks.

## Documentation

- [Documentation index](docs/README.md)
- [Product references](docs/product/README.md)
- [Architecture references](docs/architecture/README.md)
- [Operations and runbooks](docs/operations/README.md)
- [Current PAR stage](docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md)
- [Current PAR evidence](docs/evidence/README.md)
- [Historical stage archive](docs/archive/README.md)
- [Handoff boundary](docs/handoff/README.md)

Historical reports are evidence for the run in which they were produced; they
are not cached proof of the current checkout. Current acceptance must be
executed from the root command surface.

## Safety

Do not commit real `.env` files, credentials, private endpoints, department
documents, uploads, databases, logs, caches, vectors, model payloads, or local
outputs. New PA local runtime state belongs under the ignored root `.local/`
tree; Docker state belongs in named volumes or configured external storage.
Existing legacy runtime data is preserved in place until an explicit backed-up
migration is approved. See
[docs/operations/LOCAL_RUNTIME_DATA.md](docs/operations/LOCAL_RUNTIME_DATA.md).
Use sanitized fixtures only. Mutation-capable operations require an explicit
invocation and must preserve confirmation, audit, history, and citation
contracts.

The PAR architecture-reorganization stage is complete. The clean-clone
handoff and remaining release-owner actions are recorded in
[docs/handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md](docs/handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md).
