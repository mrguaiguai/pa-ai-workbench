# PA AI Workbench Architecture

## System boundary

```text
Operator
  -> apps/pa-web (operator workspace)
  -> apps/pa-api (application API, history, audit, citation contracts)
  -> packages/agent-runtime (professional workflows)
  -> packages/knowledge-engine (adapter and evidence normalization)
  -> platform/weknora (native knowledge and Agent platform)
```

The Web, API, and shared packages handle presentation, workflow semantics,
business persistence, confirmation, history, audit, and citation behavior.
WeKnora provides knowledge bases, documents, chunks, retrieval, knowledge chat,
Wiki, AgentQA, custom Agents, tools, MCP, Web Search, models, parsers, vectors,
and connectors.

## Repository modules

| Path | Responsibility |
| --- | --- |
| `apps/pa-web` | React workspace, operator workflows, status and evidence UX |
| `apps/pa-api` | FastAPI application service, business DB, safe response normalization |
| `packages/agent-runtime` | Professional workflow and orchestration implementations |
| `packages/knowledge-engine` | WeKnora adapter and evidence normalization |
| `platform/weknora` | WeKnora runtime, UI, and source |
| `infra` | shared Compose, Docker, Helm, and environment examples |
| `scripts` | root developer, operations, release, and validation commands |
| `tests` | repository boundary and final acceptance contracts |
| `docs` | current documentation, evidence, handoff, and archive separation |

## Runtime and data flow

The frontend calls only PA API contracts. The API delegates platform work
through the shared Knowledge Engine adapter rather than issuing unrelated raw
native calls. Native results are normalized into PA status, evidence, history,
and audit models before reaching the frontend.

The application persists conversations, outputs, business document records,
safe status snapshots, audit events, and citation locator metadata. WeKnora
maintains the chunks, vectors, model/provider configuration, parsers, Wiki
platform state, and Agent/tool execution used by its runtime.

New local PA runtime state uses the ignored repository-root `.local/` boundary;
container deployments use named volumes or external storage. Existing legacy
runtime state remains discoverable by path-presence compatibility checks so a
repository reorganization cannot silently switch databases or uploads. No
runtime payload is part of the source or evidence architecture.

## Evidence and safety

Document chunks, Wiki pages, and supported Web/Agent references may become
evidence only when they carry stable traceable identity. Service readiness,
provider catalogs, tool lists, vector-store state, and model configuration are
status—not evidence.

Credentials, private endpoints, uploaded bodies, raw prompts, raw provider
responses, embeddings, vectors, logs, and database contents must not cross the
safe API/report boundary or enter Git.

## Delivery architecture

- Root `compose.yaml` is the unified product entry; delivery definitions
  live under `infra`.
- Root `Makefile` is the public command entry; implementations live under the
  four `scripts` command groups.
- Component-internal entrypoints stay beside their build/runtime owner.
- GitHub workflows and repo-local Skills live at root `.github`.
- Current stage governance lives in `docs/stages/current`; current evidence is
  separate from `docs/archive`.

Detailed native capability boundaries are maintained in
[docs/architecture/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md](docs/architecture/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md).
Native source provenance and the integration patch inventory are maintained
in [platform/weknora/UPSTREAM.md](platform/weknora/UPSTREAM.md) and
[platform/weknora/PA_PATCHES.md](platform/weknora/PA_PATCHES.md); repository
license boundaries are indexed by [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
The repository-reorganization target and invariants are defined in
[docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md](docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md).
