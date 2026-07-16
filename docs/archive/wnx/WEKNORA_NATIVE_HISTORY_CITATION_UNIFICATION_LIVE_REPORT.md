# WeKnora Native History/Citation Unification Live Report

> Task: `WNX-P1-07`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P1-07` is PASS for the PA history and citation unification slice.

PA now exposes a consistent history contract for native workflow outputs:
traceable WeKnora document/Wiki citations are counted as locatable evidence,
while native outputs without traceable references fail closed with an explicit
`citation_blocked` state and visible blocker reason. The live smoke validated
native knowledge-chat citation persistence/locator behavior and native AgentQA
history persistence with a visible citation blocker.

This PASS does not claim AgentQA citation completion. Native AgentQA still
emitted zero traceable references in the live run, so the AgentQA/custom Agent
capability remains `live-partial`.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| PA Backend History | `/api/history`, `/api/history/{output_id}` | Adds `traceable_citation_count`, `citation_blocked`, `citation_blocker`, and `citation_blocked` evidence filtering. |
| PA Citation Locator | `/api/citations/locate` | Keeps document chunk locators live and normalizes Wiki deep links to `#/wiki?slug=...`. |
| Native knowledge-chat | `/api/rag/knowledge-chat` | Persists PA history/output/citations and exposes locatable native references. |
| Native AgentQA | `/api/analysis/native-agentqa` | Persists PA history/output and records visible `CITATION_BLOCKED` when native references are absent. |
| PA Frontend Shell | History page | Shows native task labels, traceable citation count, `引用阻断` filter/state, and blocker reason. |
| Validation | `backend/scripts/check_weknora_native_history_citation.py` | Runs current-run live API plus browser workflow validation. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_history_citation.py --browser
```

Sanitized output:

```text
WeKnora native history/citation unification
- decision: PASS
- evidence_type: live_api+browser_current_run
- knowledge_chat: saved_citations=2 traceable=2 locator=located
- agentqa: saved_citations=0 traceable=0 citation_blocked=true
- history: filters distinguish WeKnora and citation_blocked outputs
- browser: History page rendered native workflow evidence states
```

Additional validation:

```text
backend/.venv/bin/python -m py_compile ... -> PASS
frontend bundled node tsc --noEmit -> PASS
frontend bundled node vite build -> PASS
git diff --check -> PASS
acceptance harness static/live status -> PASS, groups=15 live=8 partial=4 blocked=0 backlog=3
sensitive scan -> reviewed benign code-field/self-test hits only
```

Evidence boundaries:

- The smoke starts a temporary PA backend/frontend and uses a temporary SQLite
  database/uploads directory.
- The knowledge-chat path uploads a sanitized current-run document, waits for
  native indexing, runs native WeKnora knowledge-chat, reads PA history detail,
  and locates the saved citation.
- The AgentQA path runs native AgentQA. Because the live native response emits
  no traceable references, PA records `citation_blocked=true` instead of
  fabricating citations.
- The browser check renders the real History page and verifies native workflow
  labels, traceable citation count, and citation-blocked visibility.
- The report and smoke output do not print service tokens, raw answers, raw
  chunks, provider payloads, `.env` values, logs, private endpoints, or private
  keys.

## Coverage Impact

The `History/citation/product shell` group moves from `live-partial` to
`live-full` because PA now validates all native output paths against a single
history/citation contract: locatable references when available, visible
fail-closed blockers when native references are insufficient.

Current coverage becomes:

```text
9.75 / 15 = 65.0%
```

The final 80% target remains unchanged at:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- AgentQA/custom Agent remains `live-partial` until native AgentQA emits
  traceable references or PA receives a documented native citation shape.
- Advanced history analytics and bulk citation migration remain outside this
  internal-production slice.
- Status/config/provider readiness must continue to stay outside citation PASS;
  only traceable document/Wiki references count as citations.
