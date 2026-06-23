# P3-M2 Release Checklist

This checklist defines the M2 release gate for PA AI Workbench using WeKnora as
the real RAG / Wiki backend. It is stricter than M1 and separates static
fixture checks from live side-effecting checks.

Do not record real tokens, private endpoints, workspace ids, KB ids, uploads,
databases, logs, raw WeKnora responses, full prompts, or long evidence excerpts
in this file or in release notes.

## Commands

Static and fixture-only gate:

```bash
backend/.venv/bin/python backend/scripts/check_m2_release.py --static-only
```

Full live release gate in an approved intranet environment:

```bash
backend/.venv/bin/python backend/scripts/check_m2_release.py --run-live-smokes
```

Default mode intentionally does not run live side-effecting smokes and should
not be treated as release READY:

```bash
backend/.venv/bin/python backend/scripts/check_m2_release.py
```

## Blocking M2 READY Gates

- [ ] Static/fixture gates pass.
- [ ] DeepSeek Chat smoke passes through PA `ModelGateway`.
- [ ] DashScope Embedding is present in WeKnora.
- [ ] KB `embedding_model_id` is non-empty and points to an Embedding model.
- [ ] Vector dimension probe passes.
- [ ] Redis/task queue gate passes.
- [ ] DocReader gate passes.
- [ ] WeKnora RAG live gate returns non-mock evidence.
- [ ] WeKnora Wiki live gate passes.
- [ ] Agent real LLM smoke passes with non-mock citation.
- [ ] Wiki real LLM draft + publish + retrieve passes.
- [ ] mock/fallback evidence is not counted as release pass.
- [ ] git safety gate passes.

## Static / Fixture Gates

The release checker runs these without live WeKnora side effects:

- Python compileall for `knowledge_engine`, `backend/app`, and `agent`.
- WeKnora adapter error mapping.
- RAG debug API and parameter validation.
- Citation contract and fail-closed behavior.
- Evidence dedup/score display fixture.
- Document processing recovery fixture.
- Wiki status recovery fixture.
- WeKnora logging redaction fixture.
- PA task / adapter request id propagation fixture.
- History filters fixture.
- Pilot feedback docs smoke.
- Intranet runbook docs smoke.
- Release checklist presence and required term check.
- Git safety check.

## Live Gates

Run live gates only with `--run-live-smokes`.

Expected live side effects:

- `check_m2_preflight.py` may run vector/retrieve probes and a tiny sanitized
  upload/index probe.
- `smoke_weknora_agent_real_llm_m2.py` uploads one sanitized Markdown fixture
  and runs QA, policy, and case workflows through the real LLM path.
- `smoke_wiki_real_llm_m2.py` uploads one sanitized fixture, creates and
  publishes one generated PA Wiki page, then polls WeKnora retrieval.

Live gates prove:

- DeepSeek Chat is reachable through PA `ModelGateway`.
- WeKnora KnowledgeQA uses DeepSeek.
- WeKnora Embedding uses DashScope/Aliyun.
- KB `embedding_model_id` is valid.
- Vector dimension is compatible.
- Redis, DocReader, and vector store are healthy.
- WeKnora RAG and Wiki are live.
- Agent and Wiki draft outputs use real LLM and real non-mock citations.

## Failure Policy

- Any blocking gate failure means M2 is `NOT READY`.
- Default mode is `NOT READY` because live gates are not executed.
- `--static-only` can pass only the static gate; it is not a release approval.
- `--run-live-smokes` is required for M2 READY.
- If a live gate is skipped, mock/fallback evidence must not be counted as pass.
- If a gate fails because of config, use `docs/PHASE3_M2_INTRANET_RUNBOOK.md`.
- If a gate exposes a product or data issue, file it with
  `docs/PHASE3_M2_PILOT_FEEDBACK_TEMPLATE.md`.

## Privacy Rules

- Do not print or commit service tokens, API keys, private endpoints, workspace
  ids, KB ids, raw logs, raw WeKnora responses, uploads, databases, or real
  pilot documents.
- Keep evidence excerpts short and sanitized.
- Use `task_id`, `document_id`, `wiki_page_id`, `output_id`, `trace_id`,
  `correlation_id`, and `adapter_operation_id` for troubleshooting.
- Keep live smoke fixtures synthetic and disposable.

## Release Record

- Release candidate:
- Operator:
- Date:
- Static command result:
- Live command result:
- DeepSeek Chat gate:
- DashScope Embedding gate:
- KB `embedding_model_id` gate:
- WeKnora RAG gate:
- WeKnora Wiki gate:
- Agent real LLM gate:
- Wiki real LLM gate:
- Git safety gate:
- Decision: READY / NOT READY
- Notes:
