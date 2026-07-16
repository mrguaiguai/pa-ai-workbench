# WeKnora Upstream Record

This directory contains the PA-controlled WeKnora native platform source.
It is intentionally kept as a self-contained Go and multi-runtime workspace
inside the PA AI Workbench monorepo.

## Upstream identity

| Field | Recorded value |
| --- | --- |
| Project | WeKnora |
| Upstream repository | <https://github.com/Tencent/WeKnora> |
| Go module | `github.com/Tencent/WeKnora` |
| Imported version marker | `0.6.0` from [`VERSION`](VERSION) |
| Official `v0.6.0` tag commit | `b0094ff47917b5abece91acff4c7e16710368f2c` |
| Reconstructed upstream source anchor | `482686d17ee89aefea54cf05bf843c04d152db27` (`feat(chat): implement local image resolver for multimodal chat`) |
| Primary license | Tencent WeKnora MIT license and bundled third-party notices in [`LICENSE`](LICENSE) |
| Local native import commit | `42a6f0ac810dd04a64a6b0999b06554ac76a5e0b` (`chore: initialize WeKnora native baseline`) |
| Coherent PA/native baseline | `e7b258c61d56bd44ce477ef29cf761d8ab07cdfc` (`par-p0-01-coherent-baseline-20260714`) |

## Provenance reconstruction

The local native import is a root commit, so its parent does not retain an
upstream SHA. `PAR-P3-03` reconstructed provenance on 2026-07-15 from the
official Tencent repository without adding or changing a remote in the PA
repository:

1. the official `v0.6.0` ref resolves to `b0094ff...`;
2. the import tree differs from that tag in 520 paths, so `VERSION=0.6.0`
   cannot be treated as an exact source-commit claim;
3. all 358 official commits reachable from fetched refs between 2026-05-20
   and the local import timestamp were compared by Git blob identity;
4. `482686d...` is the unique minimum-difference candidate: the import differs
   from it in 25 paths, with 12 local-only paths and no upstream-only paths;
5. after excluding six unmistakable PA bootstrap documents/scripts, 19 native
   paths remain changed or added at import time.

`482686d...` is therefore the reproducible reconstructed upstream source
anchor, not a claim of tree equality. The exact source SHA originally selected
by the importer was not recorded and cannot be proved from the surviving
lineage. Future syncs must preserve this distinction. The local import commit
and coherent baseline remain the authoritative Git references for the source
actually controlled by PA; the complete native delta is recorded in
[`PA_PATCHES.md`](PA_PATCHES.md).

## Controlled platform boundary

WeKnora continues to own the native implementation of:

- knowledge bases, documents, parsing, chunking, indexing, embeddings,
  retrieval, reranking, RAG, and knowledge chat;
- native Wiki pages, graph/index maintenance, Wiki tools, and Wiki evidence;
- AgentQA, custom Agents, ReACT execution, built-in tools, Agent Skills, and
  suggested questions;
- MCP services, tools, resources, prompts, approval policy, and execution;
- Web Search providers and AgentQA Web Search integration;
- model/config, parser engines, vector stores, data-source connectors, FAQ,
  tags, favorites, and platform administration;
- the native Go server and SDKs, CLI, native Vue frontend, docreader,
  migrations, deployment assets, and native runtime tests.

PA AI Workbench remains outside this directory and owns the product shell,
BFF normalization, business history, citations, audit, confirmation gates,
professional workflows, and safe status presentation. PA must use its adapter
boundary rather than reimplementing the native capabilities listed above.

## Update policy

Future upstream synchronization must:

1. record the verified upstream repository and exact source commit;
2. compare upstream source against this directory before applying changes;
3. preserve the PA exception areas listed in [`PA_PATCHES.md`](PA_PATCHES.md);
4. keep credentials, databases, uploads, logs, caches, output, vectors, and
   personal documents outside the source sync;
5. run native Go, Docker/build-context, PA adapter, citation/history/audit,
   MCP, Web Search, and browser acceptance before advancing the controlled
   baseline.

If an exact source commit cannot be established, record a quantified
reconstruction as above and do not relabel a version tag as the imported
source commit.
