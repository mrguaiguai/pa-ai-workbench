# PA AI Workbench Notice

PA AI Workbench is an independent product under `pa-ai-workbench/`. It is not a WeKnora sub-product, and this repository must not modify the outer WeKnora source tree.

## WeKnora Source Reference

Phase 2 uses the outer WeKnora repository as an engineering reference for RAG, Wiki, chunking, retrieval, and evidence workflow design.

The audited WeKnora source is identified in:

- `docs/WEKNORA_RAG_SOURCE_MAP.md`

Upstream WeKnora license notice reviewed for Phase 2:

```text
Copyright (C) 2025 Tencent. All rights reserved.

This project is licensed under the MIT License except for the third-party
components listed in the upstream WeKnora LICENSE file.
```

## Extraction Policy

PA AI Workbench follows these rules when extracting or rewriting WeKnora-inspired functionality:

- Prefer Python rewrites under PA module boundaries instead of copying Go source files.
- Keep extracted work inside `knowledge_engine/`, `agent/`, `backend/`, or other PA-owned directories.
- Preserve the WeKnora copyright and MIT attribution when a future implementation copies or substantially adapts WeKnora source.
- Add a local source note near any future substantially adapted module that identifies the upstream WeKnora module path and the adaptation strategy.
- Do not copy upstream third-party vendored code into this repository; use PA package manifests and dependency metadata instead.
- Do not commit `.env`, API keys, databases, uploads, logs, generated build output, local caches, or real department materials.

## Current Extraction Status

As of G2, PA AI Workbench contains no copied WeKnora product implementation code for the Phase 2 RAG / Wiki extraction. The repository contains an audit document and this notice so future extraction tasks can preserve attribution deliberately.

| Area | Current status | Attribution handling |
| --- | --- | --- |
| Chunker | Not yet implemented for Phase 2 | Future Python rewrite should reference `../internal/infrastructure/chunker/` if substantially adapted. |
| Retriever | Not yet implemented for Phase 2 | Future Python rewrite should reference `../internal/application/service/retriever/` and related types if substantially adapted. |
| EmbeddingProvider | Not yet implemented for Phase 2 | Implement PA-owned mock and OpenAI-compatible providers; do not copy WeKnora provider adapters. |
| Wiki | Not yet implemented for Phase 2 | Future Wiki schema/workflow should reference `../internal/types/wiki_page.go` and `../internal/application/service/wiki_*` if substantially adapted. |
| Agent evidence workflow | Not yet implemented for Phase 2 | Reference WeKnora chat/wiki flow only; PA tools must use ModelGateway and Knowledge Engine boundaries. |

## Maintenance

Update this file whenever Phase 2 introduces code that is copied from, substantially adapted from, or closely derived from WeKnora source. Keep `docs/WEKNORA_RAG_SOURCE_MAP.md` as the detailed module map and this file as the concise attribution record.
