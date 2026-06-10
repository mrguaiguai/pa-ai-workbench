# P3-M2-D2 Request Id Propagation

This note defines how PA user operations are linked to WeKnora adapter calls
without logging user prompts, document body text, tokens, or private endpoints.

## Log Event

WeKnora adapter calls emit structured JSON through logger
`pa_ai_workbench.weknora` with event name `weknora_adapter_call`.

Core fields:

- `request_id`: unique id for one adapter HTTP request lifecycle.
- `adapter_operation_id`: same stable id as `request_id`; use this as the
  adapter operation id in support notes.
- `correlation_id`: PA-side id for one user action or debug trace.
- `operation`: sanitized method and path, without host or query string.
- `status`, `status_code`, `duration_ms`, `retry_count`, `error_code`.
- `excerpt`: short redacted status or error summary.

PA context fields, present when available:

- `task_id`
- `conversation_id`
- `document_id`
- `wiki_page_id`
- `output_id`

## Propagation Points

- Analysis runs set `correlation_id`, `task_id`, and `conversation_id` while
  Agent retrieval calls WeKnora through the Adapter.
- Document upload, status refresh, and chunk preview set `correlation_id` and
  `document_id`.
- Wiki create, update, publish, and publish retrieve checks set
  `correlation_id`, `wiki_page_id`, `output_id`, and source `task_id` when the
  Wiki was generated from an output.
- RAG debug sets `correlation_id` to the API `trace_id`.
- RAG retrieve sets a fresh `correlation_id`.

## Troubleshooting

From a user-visible task:

1. Search logs for `task_id`.
2. Copy the related `adapter_operation_id`.
3. Inspect `operation`, `status_code`, `retry_count`, and `error_code`.
4. Use `correlation_id` to group all adapter calls from the same PA operation.

From an adapter error:

1. Search logs for `adapter_operation_id` or `request_id`.
2. Use `task_id`, `document_id`, `wiki_page_id`, or `output_id` to return to
   the PA record.
3. Use `excerpt` only as a short clue; do not expect raw WeKnora response text.

## Redaction Rules

Do not log:

- service tokens, API keys, authorization headers, secrets, passwords;
- full user prompts or long generated content;
- full document/chunk body text;
- private hostnames, full URLs, or query strings;
- raw WeKnora response payloads.

Only ids, sanitized operation names, status metadata, retry counts, error codes,
and short redacted excerpts should cross the log boundary.
