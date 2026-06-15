# Phase 4 Real RAG Matrix Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G3 RAG debug / retrieve 24-question real hit matrix |
| Test time | 2026-06-15 16:47:55 CST |
| Test environment | Local PA AI Workbench CLI using PA `WeKnoraApiBackend.retrieve` |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL configured; service token configured; workspace configured; default KB configured; token and endpoint intentionally omitted |
| Test scope | P4Q-001 to P4Q-024 from `backend/fixtures/phase4_rag_wiki_qa/questions.json`; `top_k=8`; current P4-G2 `external_doc_id` set |
| Test result / 测试结果 | PARTIAL / 部分通过 |

## Summary

| Result | Count | Meaning |
| --- | ---: | --- |
| PASS | 19 | Expected anchor was found in `top_k`, source was `weknora_api`, and source_type requirements were satisfied for this stage |
| PARTIAL | 1 | Retrieval returned usable live evidence but also showed a no-answer or refusal risk |
| FAIL | 1 | Required RAG behavior failed because a forbidden distractor was retrieved for a distractor-suppression question |
| BLOCKED | 3 | Wiki-only live retrieval depends on P4-G4 Wiki draft / publish / indexed / retrievable evidence |

All executed retrieve calls used current P4-G2 `external_doc_id` values and returned real `source=weknora_api` document evidence. P4-G3 did not publish Wiki pages and did not execute `knowledge_qa`.

## Current P4-G2 Evidence Scope

| Anchor | Current external_doc_id |
| --- | --- |
| TEST-RAG-001 | `761360a7-f0b7-4c4b-81f3-b5216c449975` |
| TEST-RAG-002 | `24466dc4-d787-405d-818d-fea393261d7c` |
| TEST-RAG-003 | `fcea6be6-5a34-4b5b-8a56-d169b1ac94ca` |
| TEST-RAG-004 | `184d0831-c415-4f74-834e-7d8d69b382ec` |
| TEST-RAG-005 | `09c22dfe-7c8b-4897-a211-5d6d2c3af0b0` |
| TEST-RAG-006 | `1f36ebbc-95b6-494d-87fb-b6e48345e1d0` |
| TEST-RAG-007 | `6416d9e2-f48c-4ac3-b55e-92e81669393a` |
| TEST-WIKI-001 | `e560bf34-8487-4603-ac0e-77ac8193ddc0` |
| TEST-DISTRACTOR-001 | `e52069e4-355f-4f8c-9871-7a341b1d74ea` |

## 24-Question Matrix

| Question | Scope | Expected anchors | Actual anchor result | source_type | Evidence / trace_id | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P4Q-001 | document | TEST-RAG-001 | Expected anchor found in top_k; other anchors also retrieved | document_chunk | trace_id=`p4g3-81e3a41c7af1`; evidence_id=`document_chunk:de5663fd-d44f-47a7-82da-1ef1f88d3904`; chunk_id=`de5663fd-d44f-47a7-82da-1ef1f88d3904` | PASS | Expected hit was not top evidence; ranking needs review |
| P4Q-002 | document | TEST-RAG-002 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-efe2f4595597`; evidence_id=`document_chunk:75dc9744-7955-4073-9d26-f9b9a6cd7138`; chunk_id=`75dc9744-7955-4073-9d26-f9b9a6cd7138` | PASS | Top evidence was FAQ, expected policy appeared at rank 2 |
| P4Q-003 | document | TEST-RAG-003 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-d339fb7ea7e0`; evidence_id=`document_chunk:4fd95697-0a25-485f-86c9-88d20ec31bef`; chunk_id=`4fd95697-0a25-485f-86c9-88d20ec31bef` | PASS | Expected anchor present but ranking is mixed |
| P4Q-004 | document | TEST-RAG-005 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-835203f36469`; evidence_id=`document_chunk:2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c`; chunk_id=`2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c` | PASS | Expected case was present; top evidence favored FAQ / rules |
| P4Q-005 | document | TEST-RAG-007 | Expected anchor found at rank 1 | document_chunk | trace_id=`p4g3-d2321241d8e9`; evidence_id=`document_chunk:c296a96d-747b-405e-a195-40905bdd7fa3`; chunk_id=`c296a96d-747b-405e-a195-40905bdd7fa3` | PASS | Strongest single-question hit |
| P4Q-006 | document | TEST-RAG-003 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-3ca824280519`; evidence_id=`document_chunk:67c1f837-82d8-4ed0-baef-830c1e7c1964`; chunk_id=`67c1f837-82d8-4ed0-baef-830c1e7c1964` | PASS | Wiki seed document chunk ranked high; should compare with rerank in later tuning |
| P4Q-007 | document | TEST-RAG-004 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-8720d3236e4f`; evidence_id=`document_chunk:5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875`; chunk_id=`5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875` | PASS | Expected rules found; similar case/FAQ chunks also retrieved |
| P4Q-008 | document | TEST-RAG-004 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-e765e82e0ba9`; evidence_id=`document_chunk:4fd95697-0a25-485f-86c9-88d20ec31bef`; chunk_id=`4fd95697-0a25-485f-86c9-88d20ec31bef` | PASS | Expected anchor appears at rank 3 |
| P4Q-009 | document | TEST-RAG-003 | Expected anchor found at rank 1 | document_chunk | trace_id=`p4g3-4749b4326195`; evidence_id=`document_chunk:5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875`; chunk_id=`5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875` | PASS | Expected anchor is present in top evidence |
| P4Q-010 | all | TEST-RAG-001, TEST-RAG-002 | Expected anchors found in top_k | document_chunk | trace_id=`p4g3-729da420efd4`; evidence_id=`document_chunk:4fd95697-0a25-485f-86c9-88d20ec31bef`; chunk_id=`4fd95697-0a25-485f-86c9-88d20ec31bef` | PASS | Cross-version policy anchors found, but rules chunks ranked ahead |
| P4Q-011 | all | TEST-RAG-003, TEST-RAG-004 | Expected anchors found at rank 1 | document_chunk | trace_id=`p4g3-ce9a93b0eba8`; evidence_id=`document_chunk:5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875`; chunk_id=`5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875` | PASS | Good rule-vs-rule hit |
| P4Q-012 | all | TEST-RAG-005, TEST-RAG-002 | Expected anchors found in top_k | document_chunk | trace_id=`p4g3-3b5b1ff28fa0`; evidence_id=`document_chunk:75dc9744-7955-4073-9d26-f9b9a6cd7138`; chunk_id=`75dc9744-7955-4073-9d26-f9b9a6cd7138` | PASS | New policy ranked well; case evidence also appeared later |
| P4Q-013 | all | TEST-WIKI-001, TEST-RAG-003, TEST-RAG-004 | Expected document anchors found; Wiki only as document chunk | document_chunk | trace_id=`p4g3-64833425bdd0`; evidence_id=`document_chunk:24f0b7eb-1a58-46de-9b15-d169ba23548d`; chunk_id=`24f0b7eb-1a58-46de-9b15-d169ba23548d` | PASS | Mixed Wiki+document citation cannot be fully judged until P4-G4 creates `wiki_page` evidence |
| P4Q-014 | document | TEST-RAG-005 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-c5701f845032`; evidence_id=`document_chunk:67c1f837-82d8-4ed0-baef-830c1e7c1964`; chunk_id=`67c1f837-82d8-4ed0-baef-830c1e7c1964` | PASS | Expected case appeared through combined Wiki seed/document chunk evidence |
| P4Q-015 | document | TEST-RAG-006 | Expected anchor found in top_k | document_chunk | trace_id=`p4g3-9772d2ed8f50`; evidence_id=`document_chunk:2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c`; chunk_id=`2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c` | PASS | Distractor also appeared in top_k; QA must avoid adopting it |
| P4Q-016 | all | TEST-RAG-005, TEST-RAG-006 | Expected anchors found in top_k | document_chunk | trace_id=`p4g3-491cfce0db21`; evidence_id=`document_chunk:75dc9744-7955-4073-9d26-f9b9a6cd7138`; chunk_id=`75dc9744-7955-4073-9d26-f9b9a6cd7138` | PASS | Expected case anchors present but not top-ranked |
| P4Q-017 | wiki | TEST-WIKI-001 | Not executed as pass candidate | n/a | trace_id=`p4g3-25339174d6a0` | BLOCKED | Requires P4-G4 Wiki draft / publish / indexed / retrievable evidence |
| P4Q-018 | wiki | TEST-WIKI-001 | Not executed as pass candidate | n/a | trace_id=`p4g3-dca6124da657` | BLOCKED | Requires P4-G4 Wiki draft / publish / indexed / retrievable evidence |
| P4Q-019 | wiki | TEST-WIKI-001 | Not executed as pass candidate | n/a | trace_id=`p4g3-e2008bc59733` | BLOCKED | Requires P4-G4 Wiki `source_type=wiki_page` evidence |
| P4Q-020 | all | none | No expected anchor; retrieved TEST-DISTRACTOR-001 and similar policy/rule chunks | document_chunk | trace_id=`p4g3-e8176230406e`; evidence_id=`document_chunk:24f0b7eb-1a58-46de-9b15-d169ba23548d`; chunk_id=`24f0b7eb-1a58-46de-9b15-d169ba23548d` | PARTIAL | Retrieval creates refusal risk; P4-G5 must verify `knowledge_qa` says evidence is insufficient |
| P4Q-021 | all | none | No expected anchor; retrieved synthetic case/FAQ chunks | document_chunk | trace_id=`p4g3-4097ac9cc131`; evidence_id=`document_chunk:2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c`; chunk_id=`2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c` | PASS | Retrieval is allowed as context, but QA must not invent real customer names |
| P4Q-022 | all | TEST-RAG-002; forbidden TEST-DISTRACTOR-001 | Expected anchor found, but forbidden distractor also retrieved in top_k | document_chunk | trace_id=`p4g3-35c6e42f9336`; evidence_id=`document_chunk:75dc9744-7955-4073-9d26-f9b9a6cd7138`; forbidden_evidence_id=`document_chunk:24f0b7eb-1a58-46de-9b15-d169ba23548d` | FAIL | Distractor suppression failed at retrieval layer |
| P4Q-023 | document | TEST-DISTRACTOR-001 | Expected distractor anchor found in top_k | document_chunk | trace_id=`p4g3-701ad2567319`; evidence_id=`document_chunk:24f0b7eb-1a58-46de-9b15-d169ba23548d`; chunk_id=`24f0b7eb-1a58-46de-9b15-d169ba23548d` | PASS | Correctly retrieves activity material for activity-only question, though rank can improve |
| P4Q-024 | all | TEST-RAG-001, TEST-RAG-002 | Expected anchors found in top_k | document_chunk | trace_id=`p4g3-f7dfb030594d`; evidence_id=`document_chunk:5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875`; chunk_id=`5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875` | PASS | Version anchors found; ranking still favors unrelated rule/distractor chunks before policy chunks |

## Risk Diagnosis

| Risk | Status | Notes |
| --- | --- | --- |
| Wiki-only questions | BLOCKED | P4Q-017 to P4Q-019 require P4-G4 to create real `source_type=wiki_page` evidence |
| Distractor suppression | FAIL | P4Q-022 retrieved the forbidden `TEST-DISTRACTOR-001` evidence alongside the correct policy evidence |
| No-answer retrieval | PARTIAL | P4Q-020 retrieved live evidence including distractor material; final refusal must be checked in P4-G5 |
| Ranking quality | Needs improvement | Many expected anchors are present in top_k but not rank 1; several first evidence scores are all `1`, reducing ranking interpretability |
| Mixed document/Wiki citations | Not complete | P4Q-013 can only verify document chunks in P4-G3; Wiki citation evidence belongs to P4-G4/P4-G5 |
| Current-run evidence isolation | Controlled | All executed non-Wiki retrievals used P4-G2 current `external_doc_id` values |

## Improvement Recommendations / 改进建议

### RAG

- Add rerank or score calibration for Phase 4 queries where expected anchors are present but irrelevant chunks rank first.
- Treat `TEST-DISTRACTOR-001` as a regression sentinel: P4Q-022 should fail if the distractor appears in top_k for a policy question.
- Expose rank, score semantics, source_type, and trace_id in the RAG debug page so users can see when an answer is correct only because the right chunk was somewhere in top_k.
- Consider a stricter per-question pass rubric for future runs: expected anchor in rank 1-3 for precise fact questions, not merely anywhere in top_k.

### Wiki

- Do not count uploaded `TEST-WIKI-001` document chunks as Wiki retrieval success.
- Run P4-G4 next to create a real Wiki slug, publish it, confirm indexed / retrievable, and then re-run P4Q-017 to P4Q-019 with `source_type=wiki_page`.

### QA

- In P4-G5, verify that `knowledge_qa` refuses P4Q-020 and P4Q-021 even when retrieval returns similar live evidence.
- In P4-G5, verify that P4Q-022 does not cite or adopt `TEST-DISTRACTOR-001` despite the retrieval-layer failure.

### Frontend

- The RAG debug UI should make forbidden or distractor anchors visually obvious during test runs.
- Add a clear Chinese label for blocked Wiki-only checks: “等待 Wiki 发布并索引后复测”.

### Config / Ops

- Keep P4-G3 reports tied to P4-G2 current `external_doc_id` values; do not compare future runs against stale uploads without recording a new run id.
- Avoid printing raw endpoints, service tokens, uploaded files, databases, or logs in RAG matrix reports.
