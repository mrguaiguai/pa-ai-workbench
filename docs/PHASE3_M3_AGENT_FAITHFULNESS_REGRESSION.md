# Phase 3 M3 Agent Faithfulness Regression

P3-M3-C4 adds an offline Agent-output regression gate for the PA evidence
contract. It uses the synthetic P3-M3-C2 golden set and checks the three public
Agent workflows: `knowledge_qa`, `policy_analysis`, and `case_review`.

## Files

- `agent/tools/faithfulness_checker.py`
- `backend/fixtures/agent_faithfulness_m3.json`
- `backend/scripts/smoke_agent_faithfulness_m3.py`
- `backend/fixtures/retrieval_quality_golden_m3.json`

## Contract

The smoke verifies:

- citation coverage for required golden-set facts;
- citation references point to available citations;
- citations remain traceable through PA `CitationChecker`;
- no-evidence runs return `NO_EVIDENCE` and render `依据不足`;
- unsupported claim sentinels produce an `UNSUPPORTED_CLAIM` warning.

`FaithfulnessChecker` is deterministic and intentionally narrow. It does not
replace human review or live LLM faithfulness evaluation. Its job is to catch
prompt/model regressions where key fixture facts lose numbered citations, a
result references a nonexistent citation number, no-evidence output stops
warning clearly, or an explicitly unsupported synthetic claim appears.

## Boundaries

The fixture source is `golden_fixture`, not `weknora_api` or `mock`. The smoke
does not call live WeKnora, does not read `.env`, and does not store or print
real source material. Live pilot acceptance still requires real WeKnora
retrieval and human review for representative PA materials.

Run:

```bash
backend/.venv/bin/python backend/scripts/smoke_agent_faithfulness_m3.py
```
