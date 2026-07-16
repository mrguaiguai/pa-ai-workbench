# Phase 5 P4-G Failure Map

## Metadata

| Field | Value |
| --- | --- |
| Task | P5-A2 convert Phase 4 real-test findings into a Phase 5 repair map |
| Created at | 2026-06-16 10:24:19 CST |
| Source phase | Phase 4 P4-G1 to P4-G7 |
| Source reports | `docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md`; `docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md`; `docs/PHASE4_REAL_RAG_MATRIX_REPORT.md`; `docs/PHASE4_REAL_WIKI_REPORT.md`; `docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md`; `docs/PHASE4_REAL_FRONTEND_REPORT.md`; `docs/PHASE4_REAL_TEST_SUMMARY.md` |
| Fixed corpus | `backend/fixtures/phase4_rag_wiki_qa/` |
| Question set | P4Q-001 to P4Q-024 |
| Phase 5 target | Real WeKnora live PASS, not PARTIAL |

This document is a planning and tracking artifact. It does not claim any Phase 5 capability is fixed. It converts the Phase 4 real-test evidence trail into a task mapped repair plan for P5-B through P5-G.

## P4-G Report Coverage

| Phase 4 task | Result | Key evidence | Phase 5 interpretation | Primary P5 tasks | Retest / 复测 |
| --- | --- | --- | --- | --- | --- |
| P4-G1 environment precheck | PARTIAL | Real config and read-only connection smoke passed; runtime WeKnora status returned unavailable / connected false | Runtime status semantics can mislead users and acceptance reports | P5-E3, P5-F4, P5-G1 | Re-run real env precheck and require `docs/PHASE5_REAL_ENV_PASS_REPORT.md` to be PASS |
| P4-G2 upload and index | PASS | 9 synthetic documents indexed and retrievable with `source=weknora_api`, `source_type=document_chunk` | Upload/index is the strongest baseline, but duplicate recovery and current-run tracking need hardening | P5-B1, P5-G2 | Re-upload or confirm fresh/current-run corpus and record current scope in `docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md` |
| P4-G3 RAG matrix | PARTIAL | 19 PASS, 1 PARTIAL, 1 FAIL, 3 BLOCKED; P4Q-022 retrieved forbidden distractor | RAG can find many anchors when scoped, but ranking, Wiki source, no-answer risk, and distractor suppression are not release-ready | P5-B1, P5-B2, P5-B3, P5-B4, P5-B5, P5-C2 | Run real RAG 24-question matrix and require all P4Q-001 to P4Q-024 PASS |
| P4-G4 Wiki closed loop | PARTIAL | Draft/publish/read and targeted Wiki retrieve passed; P4Q-017 to P4Q-019 returned 0 Wiki evidence | Wiki exists, but natural-language recall for official Wiki questions fails | P5-C1, P5-C2, P5-C3, P5-C4 | Re-run Wiki-only questions and require `source=weknora_api`, `source_type=wiki_page`, `wiki_page_id` |
| P4-G5 `knowledge_qa` | PARTIAL | 0 PASS, 19 PARTIAL, 5 FAIL; all counted citations were non-mock WeKnora citations | Workflow executes, but default retrieval is polluted by historical data and answer/citation quality is not acceptable | P5-D1, P5-D2, P5-D3, P5-D4, P5-D5 | Run true `knowledge_qa` 24-question script and require every question PASS |
| P4-G6 frontend acceptance | PARTIAL | TypeScript/build passed; visible English remains; backend HTTP not running for browser capture; status shows partial real/mock state | Frontend is diagnosable but not fully localized or browser-accepted | P5-E1, P5-E2, P5-E3, P5-E4 | Build and browser-check homepage, library, RAG debug, Wiki, QA, and history pages |
| P4-G7 summary | PARTIAL | Aggregated P4-G1 to P4-G6 and recommended RAG/Wiki/QA/frontend/config fixes | Phase 5 is a repair-and-gate phase, not another partial reporting phase | P5-A2 through P5-G7 | Final `docs/PHASE5_REAL_PASS_REPORT.md` only after P5-G1 to P5-G6 PASS |

## Cross-Cutting Failure Map

| Failure / risk | Phase 4 evidence | User impact | Required Phase 5 behavior | P5 task owner | Retest / 复测 |
| --- | --- | --- | --- | --- | --- |
| Runtime status inconsistency | P4-G1 connection smoke passed, but runtime status reported WeKnora unavailable; P4-G6 saw the same status tension | Users may see a false unavailable or false ready state | Status must distinguish configured, connected, unavailable, mock, partial, and ready in Chinese | P5-E3, P5-G1 | Env PASS report plus frontend status evidence |
| Historical live data pollution | P4-G5 default `knowledge_qa` all-source top_k retrieved older synthetic/live materials | Correct current fixture answers can be hidden behind old evidence | Acceptance runs must isolate fresh/current-run corpus or explicitly filter current document/wiki ids | P5-B1, P5-D2, P5-G2, P5-G5 | 24 QA questions must cite current Phase 5 evidence only |
| Ranking and answer-bearing chunk weakness | P4-G3 often found expected anchors outside rank 1; P4-G5 top_k=5 often missed answer-bearing snippets | Answers refuse or cite weak context even when the right document exists | RAG debug and QA should prioritize answer-bearing chunks and expose rank/score diagnostics | P5-B3, P5-D3 | RAG 24Q PASS report records rank and answer-point evidence |
| Wiki natural-language recall failure | P4-G4 targeted slug/title/anchor retrieval worked, but official P4Q-017 to P4Q-019 returned zero Wiki evidence | Wiki-only user questions fail despite a published page | Published Wiki fields must be searchable through natural-language questions | P5-C1, P5-C2, P5-C4 | P4Q-017 to P4Q-019 return `source_type=wiki_page` |
| Wiki citation/source confusion | P4-G5 Wiki questions returned document chunks only | A document chunk from the Wiki seed could be mistaken for a Wiki citation | Wiki citation must carry `source_type=wiki_page`, `wiki_page_id`, and locator support | P5-C3, P5-D2, P5-E3 | QA and frontend citation locate tests |
| Distractor suppression failure | P4-G3 and P4-G5 showed P4Q-022 retrieving/citing `TEST-DISTRACTOR-001` | Policy answers can cite activity scheduling as policy evidence | P4Q-022 must fail if the distractor is retrieved as support; P4Q-023 must still use it for activity-only questions | P5-B4, P5-D4, P5-G3, P5-G5 | P4Q-022 and P4Q-023 pass together |
| Version conflict uncertainty | P4-G5 P4Q-024 cited old/new anchors but did not confidently prioritize newer rule | Users cannot trust answers when old and new rules conflict | QA must cite both versions and explicitly prioritize the newer three-workday rule | P5-D4, P5-G5 | P4Q-024 PASS in real QA report |
| No-answer citation ambiguity | P4-G5 P4Q-020 partly refused but attached citations; P4Q-021 avoided fabrication but lacked clear insufficient-evidence cue | Searched context can look like support for unsupported claims | Refusal output must distinguish searched-but-insufficient context from supporting evidence | P5-D3, P5-E3, P5-G5 | P4Q-020 and P4Q-021 PASS with explicit insufficient-evidence handling |
| Frontend English terminology | P4-G6 found English labels across home, library, RAG debug, Wiki, QA, and history | Chinese users see mixed product/debug language | Normal pages and key debug controls must use Chinese display labels | P5-E1, P5-E4 | `rg` scan plus browser evidence |
| Browser-level acceptance gap | P4-G6 used source/build evidence because backend HTTP and browser capture were unavailable | Build success alone does not prove real UI behavior | Final frontend acceptance must run with backend available and record browser evidence | P5-E4, P5-G6 | `docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md` |

## Priority Question Map

| Question | Phase 4 result | Failure category | Expected Phase 5 behavior | P5 tasks | Retest / 复测 |
| --- | --- | --- | --- | --- | --- |
| P4Q-017 | P4-G4 FAIL; P4-G5 FAIL | Wiki natural-language recall and Wiki-only citation | Query about related policies/regulations/cases returns published `TEST-WIKI-001` Wiki page with `source_type=wiki_page`; QA cites Wiki evidence, not document chunk only | P5-C1, P5-C2, P5-C3, P5-D2, P5-G4, P5-G5 | Wiki-only retrieve and `knowledge_qa` both PASS |
| P4Q-018 | P4-G4 FAIL; P4-G5 FAIL | Wiki natural-language recall | Query about common misconceptions returns `TEST-WIKI-001` as Wiki evidence and answer mentions expected misconception points | P5-C1, P5-C2, P5-D2, P5-G4, P5-G5 | Wiki-only retrieve and `knowledge_qa` both PASS |
| P4Q-019 | P4-G4 FAIL; P4-G5 FAIL | Wiki evidence/source distinction | Answer explains Wiki evidence must be `source_type=wiki_page` and distinguishable from raw document evidence | P5-C2, P5-C3, P5-D2, P5-E3, P5-G4, P5-G5 | Wiki citation includes `wiki_page_id` and frontend can locate it |
| P4Q-020 | P4-G3 PARTIAL; P4-G5 PARTIAL | No-answer refusal with similar context | Answer says there is no evidence for a real regulator hourly-report rule; citations, if shown, are labelled searched-but-insufficient | P5-D3, P5-E3, P5-G5 | `knowledge_qa` PASS with explicit insufficient evidence |
| P4Q-021 | P4-G5 FAIL | No-answer refusal wording and citation policy | Answer must not invent a real customer name and must explicitly say the materials are synthetic / insufficient for that claim | P5-D3, P5-G5 | `knowledge_qa` PASS with no fabricated customer |
| P4Q-022 | P4-G3 FAIL; P4-G5 FAIL | Distractor suppression | Answer cites `TEST-RAG-002` for three-workday rule and does not cite `TEST-DISTRACTOR-001` as policy basis | P5-B4, P5-D4, P5-G3, P5-G5 | Real RAG and QA fail if forbidden anchor appears as support |
| P4Q-023 | P4-G5 PARTIAL | Legitimate distractor use | Activity-only question should retrieve `TEST-DISTRACTOR-001` and state it cannot be policy evidence | P5-B4, P5-D4, P5-G3, P5-G5 | P4Q-022 suppression and P4Q-023 allowed-use both PASS |
| P4Q-024 | P4-G5 PARTIAL | Version conflict | Answer cites old and new policy evidence, then prioritizes the newer three-workday rule and explains the difference | P5-D4, P5-G5 | `knowledge_qa` PASS with old/new citation pair |

## Broader 24-Question QA Buckets

| Bucket | Questions | Phase 4 QA status | Main failure mode | P5 tasks | Retest / 复测 |
| --- | --- | --- | --- | --- | --- |
| Precise facts | P4Q-001 to P4Q-005 | PARTIAL | Expected anchors or answer points missed in default top_k; some answers over-refused | P5-B1, P5-B3, P5-D2, P5-D3 | Answer-bearing evidence appears and all expected points pass |
| Article lookup | P4Q-006 to P4Q-009 | PARTIAL | Rule anchors often present but answer points incomplete or weakly supported | P5-B3, P5-D3 | Citations contain requested article fields and answer points |
| Cross-document synthesis | P4Q-010 to P4Q-013 | PARTIAL | Mixed evidence often missing one expected anchor or lacks Wiki citation for P4Q-013 | P5-B2, P5-C3, P5-D2 | Required document and Wiki source types present |
| Case review | P4Q-014 to P4Q-016 | PARTIAL | Expected case anchor can be outranked by unrelated policy/rule material | P5-B1, P5-B3, P5-D2 | Case-specific evidence and answer points pass |
| Wiki retrieval | P4Q-017 to P4Q-019 | FAIL | No `wiki_page` evidence in natural-language Wiki questions | P5-C1, P5-C2, P5-C3, P5-D2 | Wiki-only source PASS |
| Insufficient evidence | P4Q-020 to P4Q-021 | PARTIAL / FAIL | Refusal and citation semantics are not strict enough | P5-D3, P5-E3 | Explicit insufficient-evidence PASS |
| Distractor suppression | P4Q-022 to P4Q-023 | FAIL / PARTIAL | Forbidden distractor can be cited for policy question; legitimate activity question can miss it | P5-B4, P5-D4 | Both suppression and allowed-use checks PASS |
| Version conflict | P4Q-024 | PARTIAL | Old/new evidence present but newer rule not prioritized | P5-D4 | Newer three-workday rule PASS |

## Frontend Failure Map

| Page / area | P4-G6 finding | Phase 5 expected behavior | P5 tasks | Retest / 复测 |
| --- | --- | --- | --- | --- |
| 首页 | English headings and status labels such as `Chat Model`, `Embedding`, `RAG Pipeline`, `Capability`, `mock fallback`, `real ready` | Chinese labels for model/backend capability and clear partial real/mock state | P5-E1, P5-E3 | Source scan plus browser acceptance |
| 资料库 | English labels such as `Upload`, `Documents`, `Chunks`, `uploaded`, `processing`, `indexed`, `failed`, `unavailable`, `mock`, `extracted` | Chinese display labels while preserving API values internally | P5-E1, P5-E4 | Build and page text evidence |
| RAG 调试 | Controls show `Query`, `Top K`, `Source`, `Document IDs`, `Run`, `Reset`, `No evidence`, `Score unavailable` | Debug controls localized but still isolated from normal QA | P5-E1, P5-E4 | RAG debug browser evidence |
| Wiki | English labels include `Search`, `Pages`, `Reader`, `Editor`, `Publish confirmation`, `source refs`, `bindings`, `Evidence` | Publish/citation panels localized; state separation preserved | P5-E1, P5-C3, P5-E4 | Wiki page browser evidence and citation locate check |
| 知识问答 | Labels include `Evidence`, `Real WeKnora RAG`, `Mock fallback`, `Document`, `Total`, `ready`, `locatable`, `not locatable` | Chinese trust/citation labels and simple knowledge source selector | P5-E1, P5-E2, P5-E3 | QA browser evidence and payload check |
| 历史 | Phase 5 includes history in final frontend scope | History filters and citation summaries should follow the same Chinese terminology | P5-E1, P5-E4 | History page browser evidence |

## Config And Ops Map

| Issue | Phase 4 evidence | Required Phase 5 artifact | P5 tasks | Retest / 复测 |
| --- | --- | --- | --- | --- |
| Runtime health mismatch | P4-G1 and P4-G6 saw status inconsistency | PASS precheck and status explanation in runbook | P5-E3, P5-F4, P5-G1 | `docs/PHASE5_REAL_ENV_PASS_REPORT.md` |
| Duplicate synthetic upload | P4-G2 needed retry copy for duplicate `TEST-RAG-001` | Fresh/current-run upload strategy or cleanup/namespace procedure | P5-B1, P5-F4, P5-G2 | `docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md` |
| Missing repeatable scripts | P4-G reports used manual/CLI operations | RAG 24Q and QA 24Q scripts plus report checker | P5-F1, P5-F2, P5-F3 | Scripts return nonzero unless PASS |
| Backend not running for frontend browser acceptance | P4-G6 could not capture live browser evidence | Runbook and final browser PASS report | P5-F4, P5-E4, P5-G6 | Backend + frontend running during browser acceptance |
| Report safety | P4-G reports intentionally omitted tokens, private URLs, and logs | Phase 5 report checker enforces omissions and evidence fields | P5-F3 | Report checker PASS |

## Phase 5 Completion Dependencies

| Dependency | Must be true before final PASS | Blocking tasks |
| --- | --- | --- |
| Fixed corpus unchanged | Phase 4 manifest/questions/hit matrix still describe 9 docs and 24 questions | P5-A3 |
| Current-run evidence scope | RAG and QA reports can identify the fresh/current-run corpus | P5-B1, P5-G2 |
| RAG 24Q PASS | P4Q-001 to P4Q-024 all pass retrieval expectations | P5-B5, P5-G3 |
| Wiki PASS | P4Q-017 to P4Q-019 return real Wiki evidence | P5-C4, P5-G4 |
| QA 24Q PASS | P4Q-001 to P4Q-024 all pass answer/citation/refusal/distractor/version checks | P5-D5, P5-G5 |
| Frontend PASS | Chinese terminology and true status display are browser-accepted | P5-E4, P5-G6 |
| Final report PASS | P5-G1 to P5-G6 reports exist and all say PASS | P5-G7 |

## Retest Checklist / 复测清单

1. Run the fixture contract check after P5-A3 to confirm the fixed corpus still has 9 documents and 24 questions.
2. Run the current-run upload/index acceptance and record current identifiers before RAG or QA retests.
3. Run real RAG 24Q with document/wiki/all source scopes and record rank, trace_id, source_type, evidence_id, chunk_id, and wiki_page_id.
4. Run real Wiki closed-loop and verify P4Q-017, P4Q-018, and P4Q-019 produce `source_type=wiki_page`.
5. Run real `knowledge_qa` 24Q and fail the run if any item is PARTIAL, FAIL, or BLOCKED.
6. Run frontend build and browser acceptance with backend available.
7. Run Phase 5 report safety checker before committing P5-G reports.

## Non-Goals For This Map

- This map does not implement the fixes.
- This map does not change the Phase 4 reports.
- This map does not create new fixture content.
- This map does not count any Phase 5 task other than P5-A2 as complete.
