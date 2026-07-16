# WeKnora-First Frontend Browser Acceptance Report

> Task: `WF-P1-04`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: live browser + build/type check.

## Scope

`WF-P1-04` polishes the six PA product pages so each page exposes the current
WeKnora-first state without hiding mock, fallback, partial, blocked, or backlog
truth. The changed UI remains a PA product shell and does not rebuild WeKnora
native admin pages.

Covered pages:

- 首页
- 资料库
- RAG 调试
- Wiki
- 知识问答
- 历史

## Implementation Summary

- Added a shared `WeKnoraFirstStatusStrip` rendered on all six pages.
- The strip reads live `/api/status` and `/api/wiki/native/overview`.
- The strip displays:
  - live/native connectivity
  - active KB mapping status
  - native Wiki overview status
  - mock count
  - fallback count
  - partial count
  - blocked count
  - backlog count
- The strip keeps the current AgentQA citation blocker visible as backlog text:
  native AgentQA citation mapping remains blocked until traceable references are
  emitted.
- Homepage now reads the validated KB mapping from `weknora.kb_mapping`, not
  only the older capability summary.
- Mobile CSS was tightened so the new status strip and Library document rows do
  not create horizontal overflow.

## Build And Type Check

`npm` was not available in the current shell, so validation used the existing
project dependencies with the bundled Node runtime:

```bash
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/typescript/bin/tsc --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vite/bin/vite.js build
```

Result:

- TypeScript no-emit check passed.
- Vite production build passed.
- `frontend/dist` was generated locally by build validation and is not part of
  the commit.

## Live Runtime Used For Browser Acceptance

Temporary local validation services:

- Backend: `http://127.0.0.1:8018`
- Frontend: `http://127.0.0.1:5174`

The backend was started with temporary CORS origins for the frontend validation
port. No repository config was changed for this. Browser state was current-run,
not cached report evidence.

Live status source:

- `/api/status` returned `knowledge_backend=weknora_api`, `mock_mode=false`,
  WeKnora `status=connected`, and `weknora.kb_mapping.status=validated`.
- Active KB mapping used `selection_source=default` and a validated document KB.
- `/api/wiki/native/overview` returned `status=live`.

## Browser Acceptance Matrix

Desktop browser check:

| Page | Primary workflow visible | WeKnora-first strip visible | live/native | mock | fallback | partial | blocked | backlog | AgentQA citation blocker visible | Layout result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 首页 | Yes | Yes | connected | 0 | 0 | 0 | 0 | 11 | Yes | No horizontal overflow |
| 资料库 | Yes | Yes | connected | 0 | 0 | 0 | 0 | 11 | Yes | No horizontal overflow |
| RAG 调试 | Yes | Yes | connected | 0 | 0 | 0 | 0 | 11 | Yes | No horizontal overflow |
| Wiki | Yes | Yes | connected | 0 | 0 | 0 | 0 | 11 | Yes | No horizontal overflow |
| 知识问答 | Yes | Yes | connected | 0 | 0 | 0 | 0 | 11 | Yes | No horizontal overflow |
| 历史 | Yes | Yes | connected | 0 | 0 | 0 | 0 | 11 | Yes | No horizontal overflow |

Mobile viewport check at `390x844`:

| Page | WeKnora-first strip visible | live/mock/fallback/partial/blocked/backlog text visible | Overflow result |
| --- | --- | --- | --- |
| 首页 | Yes | Yes | No tracked horizontal overflow |
| 资料库 | Yes | Yes | No tracked horizontal overflow |
| RAG 调试 | Yes | Yes | No tracked horizontal overflow |
| Wiki | Yes | Yes | No tracked horizontal overflow |
| 知识问答 | Yes | Yes | No tracked horizontal overflow |
| 历史 | Yes | Yes | No tracked horizontal overflow |

Browser console:

- No console errors were observed during the final desktop six-page pass.

## Evidence Classification

| Evidence category | Result |
| --- | --- |
| live | Used for `/api/status`, `/api/wiki/native/overview`, and browser rendering of the six PA pages. |
| mock | Mock count is visible and `0`; mock evidence is not counted as PASS. |
| fallback | Fallback count is visible and `0`; hidden fallback is not counted as PASS. |
| partial | Partial count is visible and `0`; partial evidence is not counted as PASS. |
| blocked | Blocked count is visible and `0` for runtime status gates; AgentQA citation mapping remains visible as a backlog/blocker label. |
| backlog | Backlog count is visible and includes AgentQA citation mapping, native Agent picker, native Wiki mutations/admin, and P2 visibility slices. |
| fixture-only | Not used as PASS. |
| cached | Not used as PASS. |

## PASS Statement

`WF-P1-04` passes for frontend integration polish. All six PA pages now render a
live WeKnora-first status strip backed by current PA API calls, show native live
state and blocked/backlog truth plainly, preserve existing primary workflows,
and pass desktop plus mobile browser checks without tracked horizontal overflow.
