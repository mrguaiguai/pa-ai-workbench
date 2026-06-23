# WeKnora Native Expansion Acceptance Harness Report

Date: 2026-06-23

Task: `WNX-P0-04`

Branch: `weknora-first-mvp`

## Scope

This report documents the WNX stage acceptance checker added for the internal
production track. The checker guards future PASS claims; it does not upgrade
any capability group to `live-full` by itself.

Evidence type: `checker execution evidence`.

## Harness Contract

Script:

```text
backend/scripts/check_weknora_native_expansion_acceptance.py
```

The harness checks:

- required WNX reports exist for completed P0 prerequisites;
- report text has explicit evidence classification;
- unsafe evidence such as mock evidence, fixture-only evidence, cached evidence,
  and static UI is not counted as PASS;
- secret-shaped assignments, bearer tokens, private key blocks, and common key
  patterns are rejected;
- spec task board and progress log remain consistent for completed WNX tasks;
- coverage current and target scores parse from the ledger;
- current coverage below 80% is allowed only because the stage is explicitly
  still in progress;
- target coverage remains at least 80%;
- browser matrix hooks exist through the capability center desktop/mobile
  validation report;
- optional live status center validation can verify `/api/native/status` without
  printing raw payloads.

## Validation Evidence

Self-test command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py --self-test
```

Self-test result:

```text
WeKnora native expansion acceptance checker self-test passed
- positive coverage fixture accepted
- negative fixture rejected unsafe PASS evidence and secret-shaped values
```

The negative fixture proves the checker rejects unsafe `fixture-only PASS`
wording and secret-shaped values.

Static stage command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py
```

Observed static evidence:

```text
WeKnora native expansion acceptance check passed
- reports checked: 6
- completed prerequisite tasks: 6
- coverage current: 5.50/15 = 36.7%
- coverage target: 12.00/15 = 80.0%
- stage in progress: True
- browser hooks: desktop/mobile capability center report present
- live status center: not requested
```

Live status center command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py --start-pa-api
```

Observed live status center evidence:

```text
WeKnora native expansion acceptance check passed
- reports checked: 6
- completed prerequisite tasks: 6
- coverage current: 5.50/15 = 36.7%
- coverage target: 12.00/15 = 80.0%
- stage in progress: True
- browser hooks: desktop/mobile capability center report present
- live status center: live_api groups=15 live=7 partial=5 blocked=0 backlog=3
```

## PASS Boundary

`WNX-P0-04` is PASS only for the acceptance harness. The live capability PASS
for document lifecycle, chunk management, knowledge-chat, AgentQA, Wiki,
history/citation, MCP, web search, vector store, model/parser, connectors, and
organization primitives remains owned by their dedicated WNX tasks.

The harness intentionally allows the current score to remain below 80% while
the spec still has unfinished WNX tasks. It must fail once the stage is no
longer in progress and the ledger remains below the 80% target.

No `.env` values, API keys, service tokens, provider payloads, raw logs,
databases, uploads, screenshots, chunks, vectors, or private endpoints are
included in this report.
