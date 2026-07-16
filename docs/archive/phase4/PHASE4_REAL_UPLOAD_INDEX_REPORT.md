# Phase 4 Real Upload And Index Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G2 9 fixture documents real upload, index, and retrievable check |
| Test time | 2026-06-15 16:42:21 CST |
| Test environment | Local PA AI Workbench CLI using PA `WeKnoraApiBackend` adapter |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL configured; service token configured; workspace configured; default KB configured; token and endpoint intentionally omitted |
| Test scope | 9 synthetic sanitized Markdown documents from `backend/fixtures/phase4_rag_wiki_qa/manifest.json` |
| Primary run id | `p4g2-20260615163145-05d90cd6` |
| Retry run id | `p4g2-retry-20260615164103-cf08c176` for `TEST-RAG-001` duplicate recovery |
| Test result / 测试结果 | PASS / 通过 |

## Summary

| Metric | Result |
| --- | --- |
| Fixture documents expected | 9 |
| Documents uploaded with current P4-G2 evidence | 9 |
| Documents indexed | 9 |
| Documents retrievable by anchor and current `external_doc_id` | 9 |
| Evidence source | `weknora_api` |
| Evidence source_type | `document_chunk` |
| Duplicate-file events | 1 initial duplicate for `TEST-RAG-001`, recovered by sanitized retry copy |

P4-G2 did not run the 24-question RAG matrix, publish Wiki pages, or execute `knowledge_qa`. Those belong to P4-G3, P4-G4, and P4-G5.

## Document Results

| Order | Anchor | Fixture File | Upload Status | Index Status | Retrievable | Chunks | Evidence | Current Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | TEST-RAG-001 | `documents/001_old_reporting_policy.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`761360a7-f0b7-4c4b-81f3-b5216c449975`; evidence_id=`document_chunk:cf182ff0-fa01-4fc6-a100-13e55603c369`; chunk_id=`cf182ff0-fa01-4fc6-a100-13e55603c369` |
| 2 | TEST-RAG-002 | `documents/002_new_reporting_policy.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`24466dc4-d787-405d-818d-fea393261d7c`; evidence_id=`document_chunk:75dc9744-7955-4073-9d26-f9b9a6cd7138`; chunk_id=`75dc9744-7955-4073-9d26-f9b9a6cd7138` |
| 3 | TEST-RAG-003 | `documents/003_data_retention_audit_rules.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`fcea6be6-5a34-4b5b-8a56-d169b1ac94ca`; evidence_id=`document_chunk:4fd95697-0a25-485f-86c9-88d20ec31bef`; chunk_id=`4fd95697-0a25-485f-86c9-88d20ec31bef` |
| 4 | TEST-RAG-004 | `documents/004_external_publication_rules.md` | uploaded | indexed | retrievable | 1 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`184d0831-c415-4f74-834e-7d8d69b382ec`; evidence_id=`document_chunk:5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875`; chunk_id=`5b21f3d5-c3a3-421e-8ccc-d4cc08c0d875` |
| 5 | TEST-RAG-005 | `documents/005_bluebay_delay_case.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`09c22dfe-7c8b-4897-a211-5d6d2c3af0b0`; evidence_id=`document_chunk:2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c`; chunk_id=`2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c` |
| 6 | TEST-RAG-006 | `documents/006_beichen_correction_case.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`1f36ebbc-95b6-494d-87fb-b6e48345e1d0`; evidence_id=`document_chunk:de5663fd-d44f-47a7-82da-1ef1f88d3904`; chunk_id=`de5663fd-d44f-47a7-82da-1ef1f88d3904` |
| 7 | TEST-RAG-007 | `documents/007_ingestion_qa_faq.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`6416d9e2-f48c-4ac3-b55e-92e81669393a`; evidence_id=`document_chunk:c296a96d-747b-405e-a195-40905bdd7fa3`; chunk_id=`c296a96d-747b-405e-a195-40905bdd7fa3` |
| 8 | TEST-WIKI-001 | `documents/008_timeliness_wiki_seed.md` | uploaded | indexed | retrievable | 2 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`e560bf34-8487-4603-ac0e-77ac8193ddc0`; evidence_id=`document_chunk:67c1f837-82d8-4ed0-baef-830c1e7c1964`; chunk_id=`67c1f837-82d8-4ed0-baef-830c1e7c1964` |
| 9 | TEST-DISTRACTOR-001 | `documents/009_distractor_event_schedule.md` | uploaded | indexed | retrievable | 1 | `source=weknora_api`, `source_type=document_chunk`, anchor matched | external_doc_id=`e52069e4-355f-4f8c-9871-7a341b1d74ea`; evidence_id=`document_chunk:24f0b7eb-1a58-46de-9b15-d169ba23548d`; chunk_id=`24f0b7eb-1a58-46de-9b15-d169ba23548d` |

## Duplicate Recovery Note

The first full-run upload for `TEST-RAG-001` returned a real WeKnora duplicate-file error because the same fixture had already been uploaded during the one-document P4-G2 probe in this session.

Recovery action:

- A temporary synthetic sanitized retry copy was created outside the repository.
- The original fixture content was preserved and a current-run retry marker was appended.
- The temporary retry file was uploaded through PA `WeKnoraApiBackend`.
- The retry produced current `weknora_api` upload, indexed, chunk, and retrieve evidence.
- The temporary retry file was not committed.

This recovery keeps the final P4-G2 evidence current and avoids counting the earlier probe upload as the final test result.

## Risk Diagnosis

| Risk | Status | Notes |
| --- | --- | --- |
| Mock or fixture-only evidence mistaken as live | Controlled | All final document evidence uses `source=weknora_api` and `source_type=document_chunk` |
| Old cache / historical upload mistaken as current evidence | Controlled with note | 8 documents use the primary P4-G2 run; `TEST-RAG-001` uses a retry run with a unique marker after duplicate recovery |
| Duplicate file handling | Needs improvement | WeKnora duplicate detection can block repeated fixture uploads with identical content |
| Chunk count variance | Expected | Chunk counts range from 1 to 2 for these Markdown documents |
| Wiki readiness | Not tested here | `TEST-WIKI-001` was uploaded as a document chunk; Wiki draft/publish/retrieve belongs to P4-G4 |
| QA readiness | Not tested here | `knowledge_qa` answer and citation behavior belongs to P4-G5 |

## Improvement Recommendations / 改进建议

### RAG

- For repeated real test runs, add a controlled current-run marker or managed cleanup strategy so WeKnora duplicate-file detection does not block fixture re-upload.
- Preserve current `external_doc_id`, `evidence_id`, and `chunk_id` in downstream P4-G3 reports so RAG matrix results can be tied to this upload run.
- In P4-G3, compare anchor-only retrieve with actual P4Q queries to detect ranking or wording issues beyond basic retrievability.

### Wiki

- Treat the uploaded `TEST-WIKI-001` document only as source material for Wiki testing; do not count this P4-G2 document evidence as Wiki evidence.
- In P4-G4, create a separate Wiki slug and require `source_type=wiki_page` before marking Wiki retrieval as live-passed.

### QA

- In P4-G5, require `knowledge_qa` citations to reference current P4-G2 / P4-G4 evidence rather than generic knowledge-base results.
- For P4Q-020 and P4Q-021, verify that retrievable but insufficient material does not cause fabricated real-world answers.

### Frontend

- Surface duplicate-file errors as actionable user-facing messages rather than generic upload failures.
- Ensure document status distinguishes uploaded, indexed, and retrievable so users do not start QA before indexing completes.

### Config / Ops

- Do not commit uploaded files, databases, logs, raw endpoints, service tokens, or unredacted response bodies.
- Consider a cleanup or namespace convention for repeated synthetic test uploads in the same KB.
- Keep P4-G3 gated on the current P4-G2 evidence IDs listed in this report.
