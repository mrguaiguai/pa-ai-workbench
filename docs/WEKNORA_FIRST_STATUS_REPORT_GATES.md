# WeKnora-First Status Report Gates

> Task: `WF-P0-04`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: live API + live browser + fixture gate self-test.

## Scope

`WF-P0-04` makes PA status surfaces and report gates truthfully separate real/native readiness from mock, fallback, partial, blocked, backlog, fixture-only, cached, or unsafe PASS evidence.

This report is not fixture-only. The status surface PASS uses current live PA API responses and a browser-rendered homepage. Fixture evidence is limited to report-checker and capability-snapshot guard tests.

## Status Surfaces

| Surface | Live evidence | Result |
| --- | --- | --- |
| `/health` | Returned `status=ok`, service `pa-ai-workbench-backend`, version `0.1.0`. | PASS |
| `/api/status` | Returned `knowledge_backend=weknora_api`, `mock_mode=false`, WeKnora `status=connected`, capability matrix, fallback policy, and `weknora_first_status_gates`. | PASS |
| `/api/model/status` | Returned separate non-mock chat and embedding readiness with configured booleans only. | PASS |
| Homepage status cards | Browser-rendered cards show chat model, embedding model, RAG chain, and capability boundary separately. | PASS |
| Report safety checker | `check_phase5_report_safety.py` now scans `WEKNORA_FIRST_*` PASS reports for marker, live labels, required evidence fields, and unsafe PASS patterns. | PASS |

## Live API Evidence

Commands:

```bash
curl -s http://127.0.0.1:8017/health
curl -s http://127.0.0.1:8017/api/status
curl -s http://127.0.0.1:8017/api/model/status
```

Result summary:

- PA backend health: live `ok`.
- WeKnora connectivity: live `connected`, health status `ok`.
- Active backend: `weknora_api`.
- Mock mode: `false`.
- Native capability availability: 11 supported, 0 partial, 0 unsupported.
- WeKnora-first status categories:
  - live: 2
  - mock: 0
  - fallback: 0
  - partial: 0
  - blocked: 0
  - backlog: 6
- Chat model: `openai_compatible`, non-mock, configured.
- Embedding model: `openai_compatible`, non-mock, configured.

The API output exposes configured booleans only. It does not print API keys, service tokens, provider payloads, private endpoints, uploaded material, logs, caches, or database contents.

## Live Browser Evidence

Command shape:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8017 vite --host 127.0.0.1 --port 5177
```

Browser validation used system Chrome through Playwright against the temporary frontend and backend.

Visible card summaries:

| Card | Visible result |
| --- | --- |
| 对话模型 | `real 真实可用`, provider `openai_compatible`, mock mode `否`, API key `已设置`. |
| 向量模型 | `real 真实可用`, provider `openai_compatible`, dimension `1024`, API key `已设置`. |
| RAG 检索链路 | `real 真实可用`, backend `weknora_api`, WeKnora health check passed. |
| 能力边界 | `real 真实可用`, 11 supported, live/mock/partial/blocked/backlog counts, and `fixture-only PASS：禁止`. |

Browser validation explicitly checked visible text for `live：`, `mock：`, `partial：`, `blocked：`, `backlog：`, and `fixture-only PASS：禁止`.

## Report Gate Evidence

Commands:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_first_status_gates.py
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py --self-test
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md
```

Result summary:

- Status gate smoke passed.
- Report checker self-test passed.
- The checker accepts a safe `WEKNORA_FIRST` PASS report.
- The checker rejects a bad WeKnora-first PASS report that tries to count fixture-only evidence.
- The checker still preserves the existing Phase 5 safety checks.

## Unsafe Evidence Policy

| Evidence category | WF-P0-04 rule | Current status |
| --- | --- | --- |
| live | Required for sprint PASS. | Present. |
| mock | Must not count as PASS. | Labelled and blocked by report gate. |
| fallback | Must be visible; hidden fallback must not count as PASS. | Labelled by status categories. |
| partial | Must be visible; partial must not count as PASS. | Labelled by status categories and report gate. |
| blocked | Must be visible with cause. | Labelled by status categories; no current live blocker. |
| backlog | Must be visible and not counted as completed. | Six backlog items visible. |
| fixture-only | Must not count as PASS. | Browser card and checker both reject fixture-only PASS. |
| cached or old report | Must not count as current PASS. | Checker flags unsafe WeKnora-first PASS wording. |

## Blocked And Backlog Decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Backend status gates | Completed | `/api/status` now exposes WeKnora-first live/mock/fallback/partial/blocked/backlog categories. |
| Homepage status cards | Completed | Browser validation proves visible status cards show the new gate categories and fixture-only PASS rejection. |
| Report safety checker | Completed | WeKnora-first reports are scanned alongside Phase 5 reports. |
| Existing production backend on port 8000 | Not modified | The live validation used a temporary current-worktree backend on port 8017 to avoid mutating existing service config. |
| Full report taxonomy across future P1/P2 reports | Backlog | Current checker covers known `WEKNORA_FIRST_*` report classes and common safety fields; future native Agent/Wiki reports can add stricter per-report requirements. |

## PASS Statement

`WF-P0-04` is PASS with live API and live browser evidence. PA now exposes backend health, WeKnora connectivity, chat model readiness, embedding readiness, native capability readiness, blocked labels, backlog labels, and unsafe PASS policy without hiding mock, fallback, partial, fixture-only, cached, or old-report evidence.
