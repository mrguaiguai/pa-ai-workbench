# Phase 3 M3 KB / Workspace Mapping

This document defines how PA AI Workbench selects WeKnora workspace / KB targets
without relying on frontend-only hiding. It is intentionally sanitized: do not
commit real workspace IDs, KB IDs, service tokens, endpoints, uploads, database
dumps, logs, or real pilot material.

## Runtime Config

The adapter accepts these runtime variables:

| Variable | Purpose |
| --- | --- |
| `WEKNORA_WORKSPACE_ID` | Default workspace, used only at runtime. |
| `WEKNORA_DEFAULT_KB_ID` | Default KB, used only when default fallback is allowed. |
| `WEKNORA_KB_ALLOW_DEFAULT` | Allows explicit default fallback when no mapping matches. |
| `WEKNORA_KB_MAPPINGS` | JSON mapping config for business/team/pilot selectors. |

`WEKNORA_KB_MAPPINGS` may be either a list of entries or an object with
`mappings` and `allow_default`.

Sanitized example:

```json
{
  "allow_default": false,
  "mappings": [
    {
      "name": "policy-team",
      "workspace_id": "<workspace-id>",
      "kb_id": "<knowledge-base-id>",
      "selectors": {
        "business_area": "policy",
        "team": "pilot-team-a"
      }
    }
  ]
}
```

## Selector Rules

The resolver checks these selectors:

| Selector | Typical source |
| --- | --- |
| `kb_mapping`, `kb_scope`, `kb_name` | Explicit PA scope. |
| `business_area` | Document metadata, RAG filters, Wiki metadata. |
| `team`, `pilot`, `workspace`, `document_type` | Optional pilot routing metadata. |
| `kb_id`, `kb_ids`, `knowledge_base_id`, `knowledge_base_ids` | Explicit runtime KB selection. |

When mappings are configured, explicit KB IDs are allowed only if they match a
configured mapping or the default KB when default fallback is enabled. Otherwise
the adapter fails closed.

## Adapter Routing

The same resolver is used for:

| Adapter operation | Routing input | Routing output |
| --- | --- | --- |
| `upload_document()` | Upload metadata. | One KB target. |
| `retrieve()` | RAG filters. | One or more KB targets. |
| `search_wiki()` / `read_wiki_page()` | `kb_id` or default selectors. | One KB target. |
| `create_wiki_page()` / `update_wiki_page()` | `kb_id` or page metadata. | One KB target. |

The adapter adds small routing metadata such as `kb_mapping_name`,
`kb_selection_source`, and `kb_default_used` to PA-side metadata. It must not
return service tokens, endpoint URLs, raw full responses, or long document text.

## Fail-Closed Boundary

- Missing mapping with `WEKNORA_KB_ALLOW_DEFAULT=false` fails closed.
- Explicit KB outside configured mappings fails closed.
- Multi-KB retrieve uses only resolved KBs.
- Wiki read/write uses one resolved KB and must not silently fall back to another
  business area.
- Frontend filters are treated as hints only; the backend resolver enforces the
  boundary.

## Status API

`GET /api/capabilities` and `GET /api/status` expose `kb_mapping` as a sanitized
summary:

- mapping count;
- configured selector keys;
- whether default workspace / KB are configured;
- whether default fallback is allowed;
- `ids_redacted=true`.

The summary intentionally omits the concrete workspace and KB IDs.
