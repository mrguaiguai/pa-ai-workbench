# Phase 5 Real Env Preflight Report

| Field | Value |
| --- | --- |
| Report marker | PHASE5_REAL |
| Date | 2026-06-16 |
| Task | P5-G1 |
| Result | PASS |
| Scope | Real environment and configuration preflight |
| Rerun note | Rechecked against live local PA backend and frontend on 2026-06-16 Asia/Shanghai with real embedding runtime mapping |

## Verdict

P5-G1 can be marked complete.

The live PA backend, frontend, WeKnora connection, knowledge backend mode, mock mode, chat model gateway, and embedding provider are all in the expected real-test posture.

## Checks

| Check | Evidence | Status |
| --- | --- | --- |
| PA backend reachable | `GET http://127.0.0.1:8000/health` returned `status=ok` | PASS |
| PA frontend reachable | `GET http://127.0.0.1:5173/` returned HTTP `200` | PASS |
| Mock mode disabled | `/api/status` returned `MOCK_MODE=false` | PASS |
| Knowledge backend | `/api/status` returned `KNOWLEDGE_BACKEND=weknora_api` | PASS |
| WeKnora connection | `/api/status` returned `weknora.status=connected`, `connected=true`, `health_status=ok` | PASS |
| Backend capabilities | `/api/status` returned `release_eligible=true` and no partial/unsupported capability count | PASS |
| Chat model gateway | `/api/model/status` returned `chat_provider=openai_compatible`, `chat.mock=false`, `chat.configured=true` | PASS |
| Embedding provider | `/api/model/status` returned `embedding_provider=openai_compatible`, `embedding.mock=false`, `embedding.configured=true` | PASS |
| Embedding provider smoke | Minimal provider call returned provider `openai_compatible`, model `text-embedding-v3`, dimension `1024`, and a non-empty vector | PASS |

## Sanitized Runtime Evidence

`/api/status`:

```json
{
  "knowledge_backend": "weknora_api",
  "mock_mode": false,
  "weknora": {
    "status": "connected",
    "connected": true,
    "configured": true,
    "health_status": "ok"
  },
  "backend_capabilities": {
    "active_backend": "weknora_api",
    "release_eligible": true,
    "parity_summary": {
      "status_counts": {
        "supported": 11,
        "partial": 0,
        "unsupported": 0,
        "dev-only": 0
      },
      "release_evidence": true,
      "data_fact_source": "WeKnora KB/Wiki"
    }
  }
}
```

`/api/model/status`:

```json
{
  "chat_provider": "openai_compatible",
  "embedding_provider": "openai_compatible",
  "mock_mode": false,
  "configured": true,
  "chat": {
    "provider": "openai_compatible",
    "configured": true,
    "mock": false,
    "base_url_configured": true,
    "api_key_configured": true
  },
  "embedding": {
    "provider": "openai_compatible",
    "model": "text-embedding-v3",
    "configured": true,
    "mock": false,
    "base_url_configured": true,
    "api_key_configured": true,
    "dimension": 1024
  }
}
```

## Runtime Note

The backend was started with a temporary real embedding runtime mapping from the existing local DashScope credential into PA's `openai_compatible` embedding provider configuration. No credential values, private endpoints, uploads, databases, logs, raw chunks, or provider outputs are recorded in this report.

For repeatability, the next real gate run should keep the same effective embedding runtime values available to the PA backend:

- `EMBEDDING_PROVIDER=openai_compatible`
- `EMBEDDING_BASE_URL` configured for the DashScope OpenAI-compatible endpoint
- `EMBEDDING_MODEL_NAME=text-embedding-v3`
- `EMBEDDING_DIMENSION=1024`
- embedding credential configured in the local runtime

Current rerun conclusion:

- PA backend and frontend are reachable after local startup.
- WeKnora connection and backend capability status are real-ready.
- Chat model gateway is configured as a non-mock OpenAI-compatible provider.
- Embedding provider is configured as non-mock OpenAI-compatible and returned a real vector in the minimal smoke.

## Spec Decision

`PHASE5_SPEC.md` can be updated. P5-G1 is complete because every required real environment preflight check passed.
