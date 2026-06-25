# WNFC-0-04 100% Acceptance Harness Report

Date: 2026-06-24
Task: `WNFC-0-04: 100% acceptance harness`
Task type: validation/ops/deployment plus governance acceptance harness
PASS evidence type: checker execution evidence
Status: complete for the harness. This is not a final WNFC product PASS.

## 1. Scope

This task adds a WNFC checker that prevents false `14.00/14 = 100.0%` claims.
The checker is static by default and reads only the WNFC spec and WNFC evidence
reports. It does not call PA, WeKnora, model providers, third-party services,
databases, logs, or local secrets.

The checker validates:

- WNFC scored group count is exactly `14`;
- target score is exactly `14.00/14 = 100.0%`;
- Web Search exclusion is present and Web Search is the only excluded
  capability group;
- task-level `[b]` scope removals are allowed only when the user explicitly
  removes that slice from WNFC 100%;
- all non-Web-Search capability targets are `full-complete`;
- completed, blocked, or removed task rows have progress-log rows;
- completed WNFC evidence reports exist and contain task/evidence markers;
- unsafe mock, fixture-only, cached, stale, static UI, demo, or MVP evidence
  wording is not counted as PASS;
- secret-shaped assignments, bearer tokens, private keys, cloud keys, and GitHub
  tokens are rejected;
- Browser Hook Inventory includes `WNFC-P6-01` desktop/mobile matrix and
  `WNFC-P6-02` final-score proof hooks;
- default in-progress mode can pass while reporting `final_ready=false`;
- `--final` mode fails until the stage is truly complete.

## 2. Implemented File

`backend/scripts/check_weknora_native_full_completion_acceptance.py`

Key modes:

- default mode: validates guardrails and reports current readiness without
  pretending the stage is complete;
- `--self-test`: runs positive and negative fixtures for score parsing, unsafe
  evidence, secret-shaped text, final-mode blocking, and Web Search exclusion;
- `--final`: fails if the current score is not `14.00/14 = 100.0%`, any
  in-scope non-Web-Search WNFC task remains incomplete, or the final report is
  not done.

## 3. Checker Execution Evidence

Syntax validation:

```text
python3 -m py_compile backend/scripts/check_weknora_native_full_completion_acceptance.py
PASS
```

Checker self-test:

```text
WNFC acceptance checker self-test passed
- positive 14/14 fixture accepted
- negative fixture rejected unsafe PASS evidence and secret-shaped values
- final-mode fixture rejects incomplete non-Web-Search tasks
- Web Search implementation task is rejected
```

Current in-progress stage check:

```text
WNFC native full completion acceptance check passed
- evidence_type: checker_execution
- mode: in-progress
- reports checked: 22
- task rows: 23
- completed tasks: 20
- unfinished tasks: 0
- current score: 14.00/14 = 100.0%
- target score: 14.00/14 = 100.0%
- web_search: excluded
- final_ready: true
- browser_hooks: WNFC-P6-01 desktop/mobile matrix and WNFC-P6-02 final report hooks present
```

The current successful checker result confirms the WNFC scope is final-ready
after `WNFC-P6-02`.

## 4. Final Mode Negative Proof And Final Proof

The harness originally proved that `--final` fails before WNFC is complete
(`Final Mode Negative Proof`). It has now been rerun against the final stage
state and passed.

Representative output:

```text
WNFC native full completion acceptance check passed
- evidence_type: checker_execution
- mode: final
- reports checked: 22
- task rows: 23
- completed tasks: 20
- unfinished tasks: 0
- current score: 14.00/14 = 100.0%
- target score: 14.00/14 = 100.0%
- web_search: excluded
- final_ready: true
- browser_hooks: WNFC-P6-01 desktop/mobile matrix and WNFC-P6-02 final report hooks present
```

## 5. Web Search Exclusion

Web Search exclusion is enforced in two ways:

- the WNFC score contract must say `WNFC scored groups = 14` and
  `target WNFC score = 14.00 / 14 = 100.0%`;
- the baseline capability table must have exactly one excluded group, and it
  must be Web Search.

The self-test also creates a forbidden Web Search implementation task and
verifies the checker rejects it.

## 6. Browser Hook Inventory

The checker verifies the final product validation hooks already exist in the
WNFC task board:

- `WNFC-P6-01`: desktop/mobile browser matrix for local daily knowledge-base
  work;
- `WNFC-P6-02`: final report proving `14.00/14 = 100%`.

This does not substitute for the future browser matrix. It only prevents the
final report from omitting that required proof path.

## 7. Current Decision

`WNFC-0-04` is complete as a governance harness task.

This report is the harness evidence, not the final product report. The harness
supports in-progress runs with `final_ready=false` and final runs with
`final_ready=true`; the final product decision is recorded in `WNFC-P6-02`.
