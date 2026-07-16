# PA AI Workbench Product Specification

> Product: PA AI Workbench
>
> Repository role: canonical root product
>
> Current architecture stage: PAR

## Product position

PA AI Workbench is an internal productivity tool for a financial public
affairs team. It helps operators organize knowledge, ask traceable questions,
run professional analysis, maintain Wiki knowledge, and review history,
citations, and audit evidence.

The product is not a generic chat client and is not a WeKnora distribution.
PA owns the user experience, BFF semantics, business history, professional
workflow, safety controls, and evidence presentation. The controlled WeKnora
runtime owns general platform capabilities such as document parsing, chunks,
retrieval, RAG, Wiki, AgentQA, tools, MCP, Web Search, model/config, vector
stores, and data-source connectors.

## Primary workflows

1. **Knowledge library** — ingest sanitized files, URLs, or manual content;
   inspect safe status, processing stages, and recoverable failures.
2. **Intelligent dialogue** — run Quick Q&A or AgentQA with selected knowledge
   scope, multi-turn context, suggested questions, tool traces, and citations.
3. **Professional analysis** — produce policy, case, or knowledge outputs with
   evidence-aware warnings and persistent PA history.
4. **Wiki** — browse, search, draft, publish, and maintain native Wiki content
   through confirmation-gated mutation paths.
5. **Capability operations** — expose masked status and safe management for
   Agents, MCP, Web Search, models, parsers, vector stores, data sources, FAQ,
   tags, favorites, and Skills without leaking credentials.
6. **Review and audit** — locate citations, filter history, inspect audit
   events, and distinguish live, partial, blocked, fallback, and mock states.

## Evidence contract

- User-facing factual claims require traceable document, Wiki, or Web evidence.
- Evidence must carry a source type, stable evidence identity, native locator
  fields when applicable, and safe display metadata.
- Status/configuration data is not citation evidence.
- Answers without traceable references may be saved as outputs, but citation
  PASS must fail closed.
- Raw provider payloads, vectors, prompts, uploaded bodies, secrets, and local
  logs are never evidence artifacts.

## Safety and mutation contract

- Credential values remain in ignored local configuration or an external
  secret system and are never returned to the frontend.
- Destructive or external mutations require explicit confirmation and an audit
  record.
- PA stores business state and safe snapshots; it does not become the source of
  truth for WeKnora chunks, vectors, provider credentials, or platform config.
- Mock/fallback/partial/blocked states must remain visible and must not be
  presented as live completion.

## Delivery contract

The repository root is the only product entry. Development, operations,
release, and validation commands are exposed through the root `Makefile` and
`scripts/*`. The PA Web and API live under `apps`, PA packages under `packages`,
and the controlled native runtime under `platform/weknora`.

Static, live-service, live-workflow, browser, and clean-clone evidence are
separate gates. Historical reports do not substitute for current validation.
The current repository-reorganization contract is
[docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md](docs/stages/current/PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md).

## Non-goals

- Reimplementing WeKnora platform internals in PA.
- Exposing raw native/provider payloads or secrets for convenience.
- Treating a tidy directory tree, configured status, mock result, or archived
  report as live acceptance.
- Publishing real department materials or personal project artifacts.
