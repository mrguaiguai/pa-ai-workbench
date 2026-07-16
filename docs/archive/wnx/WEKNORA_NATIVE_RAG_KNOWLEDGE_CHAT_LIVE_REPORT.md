# WeKnora Native RAG And Knowledge-Chat Live Report

> Task: `WNX-P1-04`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P1-04` is PASS for native RAG + knowledge-chat.

PA now keeps RAG debug on WeKnora native search and adds a PA BFF
knowledge-chat workflow backed by WeKnora native `/api/v1/knowledge-chat`.
The workflow persists PA conversation messages, generation task/output, and
traceable citations from native references. Current-run guard is enforced for
the live validation corpus.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| WeKnora Native Adapter | `knowledge_engine/backends/weknora_api_backend.py` | Adds `run_knowledge_chat` over native SSE and maps answer/reference events into PA Evidence. |
| PA Backend BFF | `POST /api/rag/knowledge-chat` | Runs native knowledge-chat, saves PA conversation/history/output/citations, and returns runtime/current-run guard metadata. |
| PA Business DB | `Conversation`, `ConversationMessage`, `GenerationTask`, `GeneratedOutput`, `Citation` | Stores native knowledge-chat output and references without storing raw vectors, provider payloads, or credentials. |
| PA Frontend Shell | RAG debug page | Adds a native knowledge-chat panel with answer, runtime counts, warnings, and citation list. |
| Validation/Ops | `backend/scripts/check_weknora_native_rag_chat.py` | Runs live RAG search, live knowledge-chat, history/citation checks, and browser DOM validation with temporary services. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_rag_chat.py --browser
```

Sanitized output:

```text
WeKnora native RAG + knowledge-chat
- decision: PASS
- evidence_type: live_api
- rag_debug: total=1 current_run=passed
- knowledge_chat: references=2 saved_citations=2 guard=passed
- history: native_knowledge_chat output listed
- browser: RAG page rendered native knowledge-chat workflow
```

Evidence boundaries:

- The script starts temporary PA backend/frontend services, a temporary SQLite
  database, and a temporary upload directory.
- The document fixture is sanitized Markdown created by the smoke runner and is
  processed by live PA + live WeKnora.
- RAG debug is scoped to the current native knowledge id and must return
  matching native evidence.
- Knowledge-chat is scoped to the same current native knowledge id and must
  return native references that PA saves as real citations.
- The report does not print service tokens, environment-file values, private
  endpoints, raw upstream payloads, raw answers, raw chunks, vectors,
  screenshots, database files, upload paths, prompts, or provider payloads.

## Coverage Impact

The `Knowledge-chat/session chat` group moves from `backlog` to `live-full`.

Current coverage becomes:

```text
8.75 / 15 = 58.3%
```

The final 80% target remains unchanged at:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- RAG debug remains the operator search/debug surface; advanced ranking UI is
  backlog beyond this internal production slice.
- Knowledge-chat references are counted as citation PASS only when native
  `references` events provide traceable document or Wiki identity.
- This task improves RAG/chat history and citations, but full cross-workflow
  history/citation unification remains `WNX-P1-07`.
