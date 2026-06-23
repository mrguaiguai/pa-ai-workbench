# WeKnora-First KB Selection Mapping Report

> Task: `WF-P1-03`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: live PA API + live WeKnora workspace/knowledge base validation.

## Scope

`WF-P1-03` makes PA's active WeKnora workspace and knowledge-base mapping
visible through `/api/status`, then validates that mapping against live WeKnora
workspace and knowledge-base APIs. This is a status/product-shell slice, not a
knowledge-base admin UI.

The implementation does not expose service tokens, base URL values, credential
forms, raw provider payloads, uploaded content, local database paths, logs, or
runtime artifacts.

## Native Source And PA Mapping

| Area | Native source/API | PA decision |
| --- | --- | --- |
| Knowledge base routes | `internal/router/router.go`, `RegisterKnowledgeBaseRoutes` | Use native `GET /api/v1/knowledge-bases/{id}` for read-only validation. |
| Knowledge base fields | `internal/types/knowledgebase.go` | Surface safe fields only: id, name, type, counts, temporary/processing flags. |
| Workspace validation | Existing WeKnora tenant route used by live connection smoke | Use native `GET /api/v1/tenants/{workspace_id}` for read-only validation. |
| PA mapping resolver | `knowledge_engine/kb_mapping.py` | Expose active target, selection source, default usage, and mapping status. |
| PA status shell | `/api/status` | Add `weknora.kb_mapping` with configured/validated/blocked/backlog fields. |

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_kb_mapping_live.py
```

Result summary:

```text
WeKnora KB mapping smoke passed (live)
- PA endpoint: /api/status
- knowledge backend: weknora_api
- mock mode: False
- WeKnora status: connected
- mapping status: validated
- mapping validated: True
- selection source: default
- default used: True
- workspace id: 10000
- knowledge base id: 29adf20a-91db-45b5-9df1-6c608f802e8d
- knowledge base type: document
- chat mock: False
- embedding mock: False
```

What this proves:

- PA `/api/status` reports the active WeKnora mapping instead of relying on a
  hidden default.
- The current workspace id is configured and live validated.
- The current knowledge base id is configured and live validated.
- The selected KB type is visible as `document`.
- The status path distinguishes configured, validated, blocked, partial, and
  backlog states.
- The smoke rejects mock backend, mock chat, and mock embedding as PASS.

## Evidence Classification

| Evidence category | Result |
| --- | --- |
| live | Used for PA `/api/status`, PA `/api/model/status`, WeKnora workspace validation, and WeKnora KB validation. |
| fixture-only | Not used as PASS evidence. |
| mock | Not used; mock backend/model/embedding is rejected. |
| cached | Not used; old status output and old reports are not PASS. |
| partial | Not observed in this run; partial would apply if mapping resolved but live validation could not complete. |
| blocked | Not observed in this run; missing config, invalid KB, unreachable WeKnora, or ambiguous hidden defaults would block PASS. |
| backlog | Multi-KB management UI, KB CRUD, and credential-management UI remain backlog. |

## Mapping Contract

`/api/status` now includes a safe `weknora.kb_mapping` object with:

- `status`: `validated`, `configured`, `blocked`, or `backlog`
- `configured` and `validated`
- `workspace_id` and `kb_id`
- `selection_source`, `mapping_name`, and `default_used`
- `default_fallback_allowed` and `mapping_configured`
- safe `workspace` and `knowledge_base` summaries when live validation passes
- `blocked_reason` when validation cannot run
- `backlog` labels for intentionally deferred KB management work

This keeps Library, RAG debug, Wiki, AgentQA, status reports, and future
frontend polish anchored to the same active KB mapping.

## PASS Statement

`WF-P1-03` is complete for the active workspace/KB visibility and validation
slice. PA exposes the active WeKnora mapping through `/api/status`, validates it
against live WeKnora workspace and knowledge-base APIs, and keeps broader KB
management as explicit backlog.
