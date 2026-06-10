# Phase 3 M3 Retrieval Parameter Schema

P3-M3-C1 reserves a conservative PA schema for future WeKnora hybrid search,
rerank, score threshold, and retrieval debug trace. The schema is opt-in. PA
must not send hybrid or rerank knobs to WeKnora unless a request explicitly
enables them.

## Request Shape

RAG retrieve and debug requests continue to use the existing PA filters object.
The only new reserved key is `retrieval_options`:

```json
{
  "query": "sanitized query",
  "top_k": 8,
  "filters": {
    "source_type": "document_chunk",
    "kb_id": "redacted-kb-selector",
    "retrieval_options": {
      "hybrid": {
        "enabled": true,
        "keyword_weight": 0.4,
        "vector_weight": 0.6,
        "match_count": 20
      },
      "rerank": {
        "enabled": true,
        "model": "configured-rerank-model",
        "top_n": 8
      },
      "threshold": {
        "score": 0.2
      }
    }
  }
}
```

Allowed keys are intentionally small:

| Section | Keys | Notes |
| --- | --- | --- |
| `hybrid` | `enabled`, `keyword_weight`, `vector_weight`, `match_count` | Weights must be 0..1; match count is 1..100. |
| `rerank` | `enabled`, `model`, `top_n` | `model` is a configured model label, not a secret or endpoint. |
| `threshold` | `score` | Score threshold is 0..1. |

Unknown keys fail validation. The schema is safe to expose in debug because it
must not contain endpoints, API keys, raw prompts, or document content.

## Forwarding Rules

- Default request: no `retrieval_options` is sent to WeKnora.
- Explicit but disabled `rerank.enabled=false`: no rerank option is sent.
- Explicit `rerank.enabled=true`: the adapter may forward the normalized rerank
  section and debug trace must show a `rerank` stage.
- Explicit `hybrid.enabled=true`: the adapter may forward the normalized hybrid
  section and debug trace must show a `hybrid` stage.
- Threshold may be forwarded only when present.

The current WeKnora `/api/v1/knowledge-search` route is still the conservative
default. These options are reserved for deployments that have confirmed support
for the corresponding WeKnora build.

## Debug Trace

`/api/rag/debug` returns:

- `retrieval_options`: normalized request options;
- `debug_trace`: stages for `hybrid`, `rerank`, and `threshold`;
- evidence metadata containing `retrieval_debug_trace` and
  `weknora_retrieval_options_forwarded` when the WeKnora adapter handled the
  request.

This is a debugging contract, not a quality guarantee. Live rerank and hybrid
behavior must still be validated in a later task before being counted as release
readiness.
