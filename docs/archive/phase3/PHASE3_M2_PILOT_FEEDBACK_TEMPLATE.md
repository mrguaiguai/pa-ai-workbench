# P3-M2 Pilot Feedback Template

Use this template for every pilot issue before it becomes an engineering task.
Do not attach real confidential documents, raw `.env` values, API keys, private
endpoints, full prompts, full WeKnora responses, or long excerpts. Use sanitized
fixtures, short summaries, and trace ids instead.

## Intake

- Feedback id: `PILOT-YYYYMMDD-001`
- Owner:
- Reporter:
- Date:
- Environment: local / intranet / staging
- Category: bug / config / data / product feedback / out-of-scope
- Severity: blocking / high / medium / low
- Status: new / triaged / reproducing / fixed / closed

## Linked Ids

- PA task id:
- Conversation id:
- Document id:
- Wiki page id:
- Output id:
- RAG debug trace id:
- WeKnora adapter operation id:
- Related commit or release:

## Sanitized Context

- User workflow: document upload / analysis / RAG debug / Wiki draft / Wiki publish / history review / other
- Expected behavior:
- Actual behavior:
- Short sanitized query/topic summary:
- Short sanitized evidence summary:
- Source type: document_chunk / wiki_page / unknown
- Citation source: weknora_api / mock / none / mixed / unknown
- Evidence state: enough / weak / none / wrong / unknown
- Error or warning summary:

## Reproduction

1. Start from a clean browser session or named intranet environment.
2. Use sanitized fixture document or known synthetic data id:
3. Run these steps:
4. Observe this UI/API/log result:
5. Capture relevant ids from logs or UI:

## Privacy Checklist

- [ ] No `.env` values or service tokens are included.
- [ ] No private endpoint, host, workspace id, or KB id is included.
- [ ] No original document body, full prompt, raw WeKnora response, or long chunk text is included.
- [ ] Evidence excerpts are short, sanitized, and only long enough to reproduce.
- [ ] Screenshots hide names, cases, private entities, and internal paths.

## Triage Decision

- Classification: bug / config / data / product feedback / out-of-scope
- Why:
- Blocking gate:
- Regression owner:
- Target task or doc:
- Follow-up verification:

## Regression Checklist

- [ ] Add or update a fixture smoke when behavior can be reproduced without live WeKnora.
- [ ] Add or update a live smoke only when real WeKnora behavior is required.
- [ ] Confirm UI/API output stays redacted.
- [ ] Confirm adapter logs contain `correlation_id` and related PA ids.
- [ ] Confirm no mock fallback is counted as real WeKnora evidence.
- [ ] Record final command output and commit id.

## Known Scenario Samples

### Sample 1: Bug

- Feedback id: `PILOT-20260610-001`
- Category: bug
- User workflow: RAG debug
- Expected behavior: retrieve debug returns real WeKnora citations with chunk ids.
- Actual behavior: debug trace returns no evidence for a synthetic policy query.
- Linked ids:
  - RAG debug trace id: `trace-fixture-no-evidence`
  - WeKnora adapter operation id: `adapter-fixture-001`
- Sanitized context:
  - Short query summary: "policy exception handling"
  - Source type: document_chunk
  - Citation source: none
  - Evidence state: none
- Triage decision: bug
- Regression: add fixture that proves no-evidence state is visible and does not create fake citations.

### Sample 2: Config

- Feedback id: `PILOT-20260610-002`
- Category: config
- User workflow: document upload
- Expected behavior: uploaded sanitized PDF reaches indexed state.
- Actual behavior: document remains indexing and preflight reports model binding mismatch.
- Linked ids:
  - Document id: `doc-fixture-config-001`
  - WeKnora adapter operation id: `adapter-fixture-002`
- Sanitized context:
  - Error summary: "KB embedding model binding missing or mismatched"
  - Source type: unknown
  - Citation source: none
  - Evidence state: none
- Triage decision: config
- Regression: run preflight gate before accepting the environment as ready.

### Sample 3: Product Feedback

- Feedback id: `PILOT-20260610-003`
- Category: product feedback
- User workflow: Wiki publish
- Expected behavior: user understands that publish succeeded but retrieval indexing is still pending.
- Actual behavior: user expects the page to appear in RAG immediately.
- Linked ids:
  - Wiki page id: `wiki-fixture-publish-001`
  - Output id: `out-fixture-publish-001`
  - WeKnora adapter operation id: `adapter-fixture-003`
- Sanitized context:
  - Source type: wiki_page
  - Citation source: weknora_api
  - Evidence state: weak
- Triage decision: product feedback
- Regression: verify Wiki status explains syncing/indexing/retrievable states without exposing backend internals.

## Classification Guide

- Bug: behavior violates a committed acceptance criterion or existing contract.
- Config: environment, model, embedding, KB, DocReader, Redis, vector store, or deployment setting issue.
- Data: sanitized source material is malformed, unsupported, incomplete, or not representative.
- Product feedback: behavior works as designed but the workflow, copy, or UX needs refinement.
- Out-of-scope: request conflicts with Phase 3 boundaries, security rules, or current M1/M2 goals.
