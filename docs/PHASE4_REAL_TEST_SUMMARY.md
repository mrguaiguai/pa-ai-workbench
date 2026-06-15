# Phase 4 Real Test Summary And Optimization Roadmap

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G7 Phase 4 real-test summary and optimization recommendations |
| Test time | 2026-06-15 17:27:07 CST |
| Test environment | Local PA AI Workbench report aggregation from P4-G1 to P4-G6 |
| Backend source | `weknora_api` |
| Config summary | P4-G reports used `MOCK_MODE=false` and `KNOWLEDGE_BACKEND=weknora_api`; tokens, endpoints, uploads, databases, and logs are intentionally omitted |
| Test scope | P4-G1 environment precheck; P4-G2 upload/index; P4-G3 RAG matrix; P4-G4 Wiki closed loop; P4-G5 `knowledge_qa`; P4-G6 frontend acceptance |
| Test result / 测试结果 | PARTIAL / 部分通过 |

P4-G1 to P4-G6 all have report files and real-test evidence. Phase 4 real-test reporting is complete after P4-G7, but Phase 4 real capability is not a clean PASS. The strongest live capability is document upload/index/retrieval. The main remaining gaps are Wiki natural-language recall, `knowledge_qa` default retrieval isolation, distractor suppression, version conflict answering, frontend Chinese terminology, and runtime status consistency.

## Report Coverage

| Task | Report | Result | Summary |
| --- | --- | --- | --- |
| P4-G1 | `docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md` | PARTIAL / 部分通过 | Real-mode config and connection smoke passed, but runtime WeKnora status reported unavailable/connected false |
| P4-G2 | `docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md` | PASS / 通过 | 9 synthetic sanitized documents uploaded, indexed, and became retrievable as `source=weknora_api`, `source_type=document_chunk` |
| P4-G3 | `docs/PHASE4_REAL_RAG_MATRIX_REPORT.md` | PARTIAL / 部分通过 | 24-question RAG matrix found 19 PASS, 1 PARTIAL, 1 FAIL, 3 BLOCKED; distractor suppression failed for P4Q-022 |
| P4-G4 | `docs/PHASE4_REAL_WIKI_REPORT.md` | PARTIAL / 部分通过 | Wiki draft/publish/read and targeted retrieve passed, but P4Q-017 to P4Q-019 natural-language Wiki questions returned 0 Wiki evidence |
| P4-G5 | `docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md` | PARTIAL / 部分通过 | Real `knowledge_qa` ran all 24 questions with non-mock citations; 19 PARTIAL and 5 FAIL, with no full-pass questions under strict rubric |
| P4-G6 | `docs/PHASE4_REAL_FRONTEND_REPORT.md` | PARTIAL / 部分通过 | Frontend build passed and state separation exists, but many visible labels remain English and backend HTTP was not running for browser-level capture |

## Aggregate Result

| Category | PASS | PARTIAL | FAIL | BLOCKED | Current judgment |
| --- | ---: | ---: | ---: | ---: | --- |
| P4-G task reports | 1 | 5 | 0 | 0 | Reports complete, but most findings are partial |
| Upload/index | 1 | 0 | 0 | 0 | Strong enough for next tuning |
| RAG retrieval matrix | 19 | 1 | 1 | 3 | Useful baseline, not release pass |
| Wiki official questions | 0 | 0 | 3 | 0 | Natural-language Wiki recall failed |
| `knowledge_qa` strict QA | 0 | 19 | 5 | 0 | Real workflow executes, but quality is not acceptance-ready |
| Frontend acceptance | 0 | 5 page areas | 1 terminology area | 0 | Usable for diagnosis, not fully localized |

Overall status: PARTIAL / 部分通过.

This means Phase 4 produced a complete real-test evidence trail, not a completed production-quality RAG/Wiki/QA release. Do not describe Phase 4 real capability as fully passed until the failed and partial items below are retested.

## Key Evidence Index

| Area | Evidence |
| --- | --- |
| Real backend mode | P4-G reports recorded `MOCK_MODE=false`, `KNOWLEDGE_BACKEND=weknora_api`, and PA `KnowledgeBackend Adapter` usage |
| Document evidence | P4-G2 uploaded 9 fixture documents; final evidence uses `source=weknora_api` and `source_type=document_chunk` |
| RAG evidence | P4-G3 records P4Q-001 to P4Q-024, `trace_id`, `evidence_id`, `chunk_id`, expected anchors, and distractor results |
| Wiki evidence | P4-G4 created slug `phase4/p4g4-timeliness-p4g4-20260615165637-bc0fe0bd`; `wiki_page_id=c25e8000-6979-468f-afdf-3952b57c4903`; targeted `source_type=wiki_page` retrieve passed |
| QA evidence | P4-G5 ran `knowledge_qa` via `run_analysis()` -> `AgentOrchestrator` -> `KnowledgeQaWorkflow` and returned non-mock `weknora_api` citations |
| Frontend evidence | P4-G6 passed TypeScript and production build checks, then recorded visible text/status evidence for 首页, 资料库, RAG 调试, Wiki, 知识问答 |

## Cross-Cutting Risks

| Risk | Severity | Source reports | Diagnosis |
| --- | --- | --- | --- |
| Runtime status inconsistency | High | P4-G1, P4-G6 | Read-only connection smoke passed earlier, but runtime status can report WeKnora unavailable; frontend trust can be wrong or confusing |
| Historical live data pollution | High | P4-G3, P4-G5 | RAG debug can scope current P4-G2 documents, but default `knowledge_qa` all-source top_k retrieves older synthetic/live materials |
| Wiki natural-language recall | High | P4-G4, P4-G5 | Targeted slug/title/anchor queries can retrieve the Wiki page, but P4Q-017 to P4Q-019 fail without `source_type=wiki_page` evidence |
| Distractor suppression | High | P4-G3, P4-G5 | `TEST-DISTRACTOR-001` appears in policy-question retrieval and was cited by QA for P4Q-022 |
| Version conflict handling | Medium | P4-G5 | P4Q-024 cited old/new anchors but did not confidently prioritize the newer three-workday rule |
| Frontend terminology | Medium | P4-G6 | User-facing pages still show English labels such as `Query`, `Run`, `Evidence`, `Real WeKnora RAG`, and `Mock fallback` |
| Browser-level frontend evidence | Medium | P4-G6 | Build passed, but no browser screenshot was captured and local backend HTTP was not running during P4-G6 |

## Optimization Roadmap / 改进建议

### RAG

1. Add a current-run / corpus filter for acceptance runs so P4-G2 fixture evidence can be isolated from older synthetic uploads without exposing raw debug controls in normal QA.
2. Improve ranking and rerank for answer-bearing chunks, not only anchor-bearing chunks; require precise fact questions to place expected anchors in a higher rank band.
3. Keep `TEST-DISTRACTOR-001` as a standing regression sentinel. Policy questions should fail if the activity schedule is retrieved or cited as policy evidence.
4. Add richer RAG debug diagnostics for rank, score semantics, matched fields, source_type, and trace_id, especially for Wiki search fields.

### Wiki

1. Fix published Wiki natural-language retrieval for P4Q-017, P4Q-018, and P4Q-019 before counting Wiki-only QA as live passed.
2. Ensure published Wiki title, summary, body, aliases, source_refs, and metadata are indexed and searchable.
3. Distinguish user-created Wiki pages from auto-generated summary/entity pages in search results and citations.
4. Preserve the good frontend state split: draft, published but not indexed, indexing, sync failed, and retrievable must remain separate states.

### QA

1. Add a QA retrieval scope or corpus policy so default `knowledge_qa` can prefer the current validated corpus while still keeping the normal page simple.
2. Strengthen answer-point checking: citations must contain the answer-bearing snippet, not only the same broad anchor.
3. Improve no-answer refusal formatting so citations used as searched context are not displayed as supporting evidence for unsupported claims.
4. Add explicit version-conflict logic: when old and new policy evidence are both present, cite both and prioritize the newer effective rule.
5. Add a distractor guard that removes or demotes forbidden anchors when the user explicitly says not to use activity schedule material as policy evidence.

### Frontend

1. Finish Chinese terminology for normal pages: replace `Evidence`, `Real WeKnora RAG`, `Mock fallback`, `Document`, `Total`, `ready`, `locatable`, and `not locatable`.
2. Localize RAG debug controls while keeping them on the debug page: `Query`, `Top K`, `Source`, `Document IDs`, `Run`, `Reset`, and `No evidence`.
3. Localize Wiki publish/citation panels: `Publish confirmation`, `source refs`, `bindings`, `Score unavailable`, and `Evidence`.
4. Add manual or automated screenshot acceptance for 首页, 资料库, RAG 调试, Wiki, and 知识问答 after the backend is running.
5. Make partial real/mock status more visible: chat can be real while embedding, evidence, or fallback state can still be mock/partial.

### Config / Ops

1. Align runtime WeKnora health status with the successful connection smoke or document why the readiness semantics differ.
2. Provide repeatable local run commands for backend, frontend, and real-test scripts, including the bundled Node fallback when `npm` is not on PATH.
3. Add a cleanup or namespace strategy for repeated synthetic uploads to avoid duplicate-file errors and stale evidence pollution.
4. Keep P4-G reports free of raw endpoints, service tokens, uploaded files, database files, logs, and unredacted provider payloads.
5. Treat future real-test reruns as new dated reports or appendices so old evidence IDs are not confused with current acceptance evidence.

## Recommended Next Work

| Priority | Work item | Reason |
| --- | --- | --- |
| 1 | Fix `knowledge_qa` current-corpus isolation and rerun P4Q-001 to P4Q-024 | Default QA is the user-facing workflow and currently has 0 strict PASS |
| 2 | Fix Wiki natural-language retrieval and rerun P4Q-017 to P4Q-019 | Wiki exists and targeted retrieval works, but expected user questions fail |
| 3 | Add distractor and version-conflict guards | P4Q-022 and P4Q-024 are trust-critical |
| 4 | Localize frontend labels and status text | P4-G6 found visible English terminology across normal workflows |
| 5 | Resolve runtime status mismatch and backend startup routine | Frontend trust depends on accurate live/unavailable state |

## Final Acceptance Statement

P4-G7 completes the Phase 4 real-test reporting set. The project now has concrete evidence for environment, upload/index, RAG retrieval, Wiki, `knowledge_qa`, and frontend status. The result is PARTIAL / 部分通过: real WeKnora-backed document ingestion and retrieval are proven, but RAG ranking, Wiki natural-language recall, QA answer quality, distractor suppression, version handling, and frontend Chinese terminology require follow-up implementation before claiming a full Phase 4 real capability pass.
