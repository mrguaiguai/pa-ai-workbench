# WNID-0-03 Acceptance Harness Report

> Date: 2026-06-25
>
> Task: `WNID-0-03`
>
> Evidence type: checker execution evidence
>
> Scope: WNID governance/validation only; no PA product code and no WeKnora
> native source change.

## Result

`WNID-0-03` is complete as an acceptance-harness task. The new checker makes the
WeKnora Native Intelligent Dialogue final-readiness claim mechanically
checkable while preserving the current truthful stage state:

- default mode may pass while reporting `final_ready=false`;
- `--final` must fail until every in-scope WNID task is complete;
- Web Search remains in scope and is checked as a final hard gate;
- MCP tool execution remains in scope and is checked as a final hard gate;
- current-run evidence, browser matrix, final report, task rows, progress log,
  and sensitive-text guardrails are checked;
- mock/demo/fixture-only/static/cached/status-only evidence is not PASS.

## Implemented Checker

Path:

```text
backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py
```

The checker uses only Python standard library modules and performs static
governance checks against:

- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md`;
- this report when present;
- future browser matrix and final report paths when present.

Default mode is intentionally an in-progress gate. It verifies that WNID still
contains all required task rows and hard-gate language, then reports final
readiness truthfully. It does not mark AgentQA Web Search, MCP execution, Wiki
Mode, suggested questions, browser matrix, or final WNID PASS complete.

Final mode is stricter. It requires:

- every WNID task row complete;
- `WNID-P3-02`, `WNID-P4-01`, `WNID-P4-02`, `WNID-P8-01`, and `WNID-P8-02`
  complete;
- final WNID report present;
- browser matrix report present;
- Web Search and MCP execution contract phrases still present;
- no unsafe PASS wording or secret-shaped values in checked WNID documents.

## Validation Evidence

Commands run for this task:

```bash
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py --self-test
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py --final
git diff --check -- backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md
rg -n "T[O]DO|\\[T[O]DO|BEGIN (RSA|OPENSSH|PRIVATE) KEY|[A-Za-z0-9_]*(API_KEY|SERVICE_TOKEN|PASSWORD|SECRET|AUTHORIZATION)[A-Za-z0-9_]*\\s*=" backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md
```

Expected `--self-test` evidence:

```text
WNID acceptance checker self-test passed
- positive in-progress fixture reports final_ready=false
- negative fixtures reject Web Search/MCP removal and unsafe PASS wording
- final mode rejects incomplete WNID task board
```

Current normal-mode evidence after `WNID-P3-01` completion:

```text
WNID native intelligent dialogue acceptance check passed
- evidence_type: checker_execution
- mode: in-progress
- task_rows: 17
- completed_tasks: 8
- open_tasks: 9
- progress_log_entries: 8
- web_search: in_scope
- mcp_execution: in_scope
- current_run_evidence: contract_present
- browser_matrix: pending
- final_report: pending
- final_ready: false
```

Expected final-mode evidence at this point:

```text
WNID native intelligent dialogue acceptance check failed
```

That final-mode failure is correct until later WNID tasks produce live
current-run evidence for the Intelligent Conversation capability set.

## Current Blockers Preserved

The checker does not unblock capability work by itself. Later WNID tasks still
need these real inputs or recorded blockers:

- approval-gated safe MCP tool execution or denial with audit/history for
  `WNID-P3-02`;
- MCP prompt parity decision for `WNID-P3-03`;
- Web Search provider setup or credential path for `WNID-P4-01`;
- native AgentQA Web Search reference shape with provider, URL, title, snippet,
  and rank for `WNID-P4-02`;
- browser matrix and final report evidence for `WNID-P8-01` and `WNID-P8-02`.

## Non-Changes

- No WNFC conclusion was changed.
- No service was started.
- No `.env`, database, log, upload, build, screenshot, or dependency artifact
  was staged or modified.
- `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` was not touched.
