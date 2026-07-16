# PA-Controlled WeKnora Patch Ledger

This ledger records the native exceptions that PA AI Workbench must preserve
when updating or validating the controlled WeKnora platform. It separates the
reconstructed Tencent source anchor, the local import, the coherent PA/native
baseline, and later repository-only relocations so that version attribution is
not confused with PA behavior changes.

## Baselines

| Item | Value |
| --- | --- |
| Imported version marker | `0.6.0` |
| Official `v0.6.0` tag commit | `b0094ff47917b5abece91acff4c7e16710368f2c` |
| Reconstructed upstream source anchor | `482686d17ee89aefea54cf05bf843c04d152db27` |
| Local native import | `42a6f0ac810dd04a64a6b0999b06554ac76a5e0b` |
| Coherent PA/native baseline | `e7b258c61d56bd44ce477ef29cf761d8ab07cdfc` |
| PA subtree paired with the baseline | `c053ea532aabac1614e10c4f37e2863d46f3fcf1` |
| Repository relocation | `PAR-P1-01`: original tracked native paths moved beneath `platform/weknora/` |

The exact upstream SHA was not retained as a parent of the root import. The
comparison method and its limits are recorded in [`UPSTREAM.md`](UPSTREAM.md).
The reconstructed anchor is a quantified best match, not a claim that either
the import or coherent baseline is tree-identical to official upstream.

## Complete controlled native exception inventory

Relative to reconstructed anchor `482686d...`, coherent baseline `e7b258c...`
contains exactly 50 changed or added native paths after excluding the seven
PA-owned bootstrap documents and command files outside the native ownership
boundary. `M` means the upstream path was modified; `A` means the path was
added by the controlled PA lineage.

```text
M .gitignore
M README.md
M config/builtin_agents.yaml
A config/builtin_models.yaml
M docker-compose.yml
M internal/agent/act.go
A internal/agent/act_references_test.go
M internal/agent/engine.go
M internal/agent/skills/skill.go
M internal/agent/tools/knowledge_search.go
M internal/agent/tools/wiki_tools.go
M internal/agent/tools/wiki_write_page.go
M internal/application/repository/wiki_page.go
M internal/application/service/chat_pipeline/merge.go
M internal/application/service/chat_pipeline/search.go
A internal/application/service/chat_pipeline/search_scope_test.go
M internal/application/service/chunk.go
M internal/application/service/mcp_service.go
A internal/application/service/mcp_service_execution_test.go
M internal/application/service/session_knowledge_qa.go
A internal/application/service/session_search_targets_test.go
M internal/application/service/skill_service.go
A internal/application/service/skill_service_test.go
M internal/application/service/wiki_page.go
M internal/container/container.go
A internal/datasource/connector/rss/connector.go
A internal/datasource/connector/rss/connector_test.go
M internal/handler/chunk.go
M internal/handler/dto/model.go
M internal/handler/dto/model_test.go
M internal/handler/mcp_service.go
A internal/handler/mcp_service_ssrf.go
A internal/handler/mcp_service_ssrf_test.go
M internal/handler/session/agent_stream_handler.go
M internal/handler/session/helpers.go
M internal/handler/skill_handler.go
M internal/handler/web_search_provider.go
M internal/handler/wiki_page.go
M internal/mcp/client.go
A internal/mcp/client_prompt_test.go
M internal/models/rerank/aliyun_reranker.go
A internal/models/rerank/aliyun_reranker_test.go
M internal/router/router.go
M internal/types/chunk.go
M internal/types/interfaces/chunk.go
M internal/types/interfaces/mcp_service.go
M internal/types/interfaces/skill.go
M internal/types/interfaces/wiki_page.go
M internal/types/mcp.go
M internal/types/search.go
```

The seven excluded PA bootstrap artifacts are
`DEV_SPEC_副本.md`, `PA_AI_WORKBENCH_DAY1_MVP_SPEC.md`,
`PA_AI_WORKBENCH_PRODUCT_SPEC.md`, `docs/PA_WORKBENCH_QUICKSTART.md`, and the
three `scripts/pa-workbench-*.sh` launchers. They were PA product/command
artifacts rather than native WeKnora exceptions and have since been moved or
retired by the PAR path and command tasks.

## Import-to-coherent 35-path stage subset

The following 35 paths are the exact native delta from local import
`42a6f0a...` to coherent baseline `e7b258c...`. This subset explains the WNID
work added after import; it is included separately so an upstream sync can
distinguish import-time changes from later controlled behavior.

```text
.gitignore
config/builtin_agents.yaml
config/builtin_models.yaml
docker-compose.yml
internal/agent/act.go
internal/agent/act_references_test.go
internal/agent/skills/skill.go
internal/agent/tools/wiki_write_page.go
internal/application/repository/wiki_page.go
internal/application/service/chunk.go
internal/application/service/mcp_service.go
internal/application/service/mcp_service_execution_test.go
internal/application/service/skill_service.go
internal/application/service/skill_service_test.go
internal/application/service/wiki_page.go
internal/handler/chunk.go
internal/handler/dto/model.go
internal/handler/dto/model_test.go
internal/handler/mcp_service.go
internal/handler/mcp_service_ssrf.go
internal/handler/mcp_service_ssrf_test.go
internal/handler/skill_handler.go
internal/handler/web_search_provider.go
internal/handler/wiki_page.go
internal/mcp/client.go
internal/mcp/client_prompt_test.go
internal/models/rerank/aliyun_reranker.go
internal/models/rerank/aliyun_reranker_test.go
internal/router/router.go
internal/types/chunk.go
internal/types/interfaces/chunk.go
internal/types/interfaces/mcp_service.go
internal/types/interfaces/skill.go
internal/types/interfaces/wiki_page.go
internal/types/mcp.go
```

## Contract ownership by exception area

- AgentQA/ReACT and evidence: reference propagation, scoped search targets,
  stream finalization, Wiki tool evidence, and built-in Agent defaults.
- Knowledge, Wiki, chunk, and Skills: service/repository interfaces, handlers,
  controlled mutations, and coverage for PA-consumed native contracts.
- MCP: prompt parity, approval-gated execution, service contracts, client
  behavior, and SSRF protection.
- Web Search and data sources: provider routing, search target types, RSS
  connector behavior, and PA evidence integration.
- Model/rerank: built-in model metadata, DTO compatibility, and Aliyun rerank
  behavior/tests.
- Configuration/runtime boundary: native ignore rules, native README context,
  Agent/model defaults, and the original Compose definition.

The WNID final evidence is
[`docs/archive/wnid/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md`](../../docs/archive/wnid/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md).
It is PA evidence and not part of the native runtime ownership boundary.

## Path-only repository adjustments after the coherent baseline

`PAR-P1-01`, `PAR-P2-02`, and `PAR-P2-03` moved ownership boundaries without
changing the native product contracts above:

- original native `docker-compose.yml` is represented by canonical root
  `infra/compose/weknora.yaml` and the root `compose.yaml` product entry;
- canonical Dockerfiles, Helm, env examples, and workflows live under root
  `infra/` and `.github/workflows/`;
- `infra/docker/weknora/Dockerfile.docreader` still copies native `packages/`
  from the isolated `platform/weknora` build context;
- native workflow filters, working directories, Docker contexts, and artifact
  paths resolve through `platform/weknora/` from repository root;
- root command launchers resolve PA applications under `apps/`, PA packages
  under `packages/`, and native source under `platform/weknora/`;
- the root `.gitignore` owns repository-wide runtime/artifact policy while
  `platform/weknora/.gitignore` retains native-specific exclusions. Broad
  root build/output patterns remain prohibited because legitimate native Go
  source includes `internal/build` and `internal/output` paths.

The Go module remains `github.com/Tencent/WeKnora`; the native module root,
`cli`, and `client` stayed together, so imports and relative module resolution
do not change because of the relocation.

## Ownership and update guardrails

- WeKnora remains authoritative for native RAG, Document, Wiki, AgentQA, MCP,
  Web Search, model, parser, vector-store, and data-source behavior.
- PA remains authoritative for product UX, BFF contracts, business history,
  citations, audit, mutation confirmation, and professional workflow output.
- Native chunks, vectors, provider payloads, secrets, and platform config are
  not copied into PA business storage.
- Status/config readiness is not citation evidence. Missing source identity
  continues to fail closed at the PA evidence boundary.
- `.env`, databases, uploads, logs, output, caches, vectors, raw documents,
  and personal materials are outside this ledger and must not be read, moved,
  published, or overwritten by an upstream sync.

For every upstream update, compare the candidate against the reconstructed
anchor and current controlled source, review all 50 exception paths, preserve
license/notice files, and rerun affected Go tests, Docker/build-context checks,
PA adapter/citation/history/audit regressions, MCP/Web Search acceptance, PAR
governance/final diagnostics, Skill mirrors, `git diff --check`, and sensitive
pattern scans.
