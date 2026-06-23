# Phase 4 Real Knowledge QA Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G5 `knowledge_qa` 24-question real answer, citation, refusal, distractor, and version-conflict test |
| Test time | 2026-06-15T17:09:45 to 2026-06-15T17:11:56 CST |
| Test environment | Local PA AI Workbench service-layer run using `run_analysis()` -> `AgentOrchestrator` -> `KnowledgeQaWorkflow` |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; chat provider `openai_compatible`; WeKnora base URL configured; service token configured; chat key configured; tokens and endpoints intentionally omitted |
| Test scope | P4Q-001 to P4Q-024 from `backend/fixtures/phase4_rag_wiki_qa/questions.json`; default `knowledge_qa` all-source behavior; default `top_k=5`; independent conversation per question |
| Test result / 测试结果 | PARTIAL / 部分通过 |

## Summary

| Result | Count | Meaning |
| --- | ---: | --- |
| PASS | 0 | Fully satisfied answer points, citation type, expected anchors, refusal / distractor rules |
| PARTIAL | 19 | Used real non-mock citations or refused safely, but missed required answer points, source type, or complete coverage |
| FAIL | 5 | Required citation/source/answer behavior failed |
| BLOCKED | 0 | Run could not execute |

The real `knowledge_qa` workflow executed successfully and returned non-mock `weknora_api` citations for all 24 questions after allowing real network access. The overall QA result is PARTIAL because the default all-source `top_k=5` experience frequently retrieved historical test material ahead of the current Phase 4 fixture evidence, Wiki-only questions returned document citations instead of `wiki_page` citations, and several answers refused even when the expected anchor existed in lower-ranked evidence.

## Environment Evidence

| Check | Result |
| --- | --- |
| `MOCK_MODE` | `false` |
| `KNOWLEDGE_BACKEND` | `weknora_api` |
| Knowledge backend adapter | `WeKnoraApiBackend` |
| Chat provider | `openai_compatible` |
| Chat model | `deepseek-chat` |
| Evidence source | all saved citations used `source=weknora_api`; no mock citations were counted |
| First sandbox run | Network request failed, so it was not counted as the real result |
| Real network run | Completed P4Q-001 to P4Q-024 and produced this report |

## 24-Question Matrix

| Question | Type | Expected | Citation counts | Matched / forbidden anchors | Answer / refusal signal | Evidence trace sample | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P4Q-001 | precise_fact | TEST-RAG-001 | total=5; document=5; wiki=0 | matched=TEST-RAG-001; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:ac844e37-1e55-4a62-851b-7181347ce692; chunk_id=ac844e37-1e55-4a62-851b-7181347ce692; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:b9e5e04f-b28e-47bf-bcde-eaf928042ebe; chunk_id=b9e5e04f-b28e-47bf-bcde-eaf928042ebe; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-002 | precise_fact | TEST-RAG-002 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:9fd22f55-936c-4b12-91da-a1aad8dcd26e; chunk_id=9fd22f55-936c-4b12-91da-a1aad8dcd26e; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:1ad8a068-1fc3-4a24-a8a4-c3aae1b1dc1c; chunk_id=1ad8a068-1fc3-4a24-a8a4-c3aae1b1dc1c; wiki_page_id=- | PARTIAL | Default top_k retrieved live evidence but missed the expected anchor or answer point. |
| P4Q-003 | precise_fact | TEST-RAG-003 | total=5; document=5; wiki=0 | matched=TEST-RAG-003; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:b401bfce-c92d-4ba4-b377-9d495be86e01; chunk_id=b401bfce-c92d-4ba4-b377-9d495be86e01; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:5b9a4ee2-63b8-4860-b6b6-a7b2acac6a7d; chunk_id=5b9a4ee2-63b8-4860-b6b6-a7b2acac6a7d; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-004 | precise_fact | TEST-RAG-005 | total=5; document=5; wiki=0 | matched=TEST-RAG-005; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:d607fd99-c900-4a25-951c-40a8342e3f44; chunk_id=d607fd99-c900-4a25-951c-40a8342e3f44; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-001,TEST-RAG-002,TEST-RAG-003,TEST-RAG-004,TEST-RAG-005,TEST-RAG-006,TEST-WIKI-001; evidence_id=document_chunk:67c1f837-82d8-4ed0-baef-830c1e7c1964; chunk_id=67c1f837-82d8-4ed0-baef-830c1e7c1964; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-005 | precise_fact | TEST-RAG-007 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:a3cee696-a9f1-45d8-a3fc-760bded29559; chunk_id=a3cee696-a9f1-45d8-a3fc-760bded29559; wiki_page_id=-<br>document_chunk; anchors=TEST-DISTRACTOR-001; evidence_id=document_chunk:6406e813-89f3-461f-944d-885d3e586dd2; chunk_id=6406e813-89f3-461f-944d-885d3e586dd2; wiki_page_id=- | PARTIAL | Default top_k retrieved live evidence but missed the expected anchor or answer point. |
| P4Q-006 | article_lookup | TEST-RAG-003 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:43770e1a-da24-4f62-85b9-2ff12fdb4628; chunk_id=43770e1a-da24-4f62-85b9-2ff12fdb4628; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:8b5a2508-e896-4660-87d4-5fa1dcda6b96; chunk_id=8b5a2508-e896-4660-87d4-5fa1dcda6b96; wiki_page_id=- | PARTIAL | Default top_k retrieved live evidence but missed the expected anchor or answer point. |
| P4Q-007 | article_lookup | TEST-RAG-004 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:2a286511-0846-4461-b081-6dc87f01c7c0; chunk_id=2a286511-0846-4461-b081-6dc87f01c7c0; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:754ea5f7-d966-42bd-851e-6b84d302740b; chunk_id=754ea5f7-d966-42bd-851e-6b84d302740b; wiki_page_id=- | PARTIAL | Default top_k retrieved live evidence but missed the expected anchor or answer point. |
| P4Q-008 | article_lookup | TEST-RAG-004 | total=5; document=5; wiki=0 | matched=TEST-RAG-004; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:8b5a2508-e896-4660-87d4-5fa1dcda6b96; chunk_id=8b5a2508-e896-4660-87d4-5fa1dcda6b96; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:d9b67f9f-f5d3-44fd-ac6b-baa2c9a88faf; chunk_id=d9b67f9f-f5d3-44fd-ac6b-baa2c9a88faf; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-009 | article_lookup | TEST-RAG-003 | total=5; document=5; wiki=0 | matched=TEST-RAG-003; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:fd37d9e8-8f44-4458-84df-f473743d70f7; chunk_id=fd37d9e8-8f44-4458-84df-f473743d70f7; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:223465cb-b6a3-4a6c-8faa-6af67de770da; chunk_id=223465cb-b6a3-4a6c-8faa-6af67de770da; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-010 | cross_document_synthesis | TEST-RAG-001,TEST-RAG-002 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:629938b3-a95f-400f-a498-145fd344faa2; chunk_id=629938b3-a95f-400f-a498-145fd344faa2; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-003,TEST-RAG-004; evidence_id=document_chunk:1cb2ec5e-f4a3-45a6-802b-d0ca4ed3ab7d; chunk_id=1cb2ec5e-f4a3-45a6-802b-d0ca4ed3ab7d; wiki_page_id=- | PARTIAL | Default top_k retrieved live evidence but missed the expected anchor or answer point. |
| P4Q-011 | cross_document_synthesis | TEST-RAG-003,TEST-RAG-004 | total=5; document=5; wiki=0 | matched=TEST-RAG-003,TEST-RAG-004; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:8b5a2508-e896-4660-87d4-5fa1dcda6b96; chunk_id=8b5a2508-e896-4660-87d4-5fa1dcda6b96; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:ac844e37-1e55-4a62-851b-7181347ce692; chunk_id=ac844e37-1e55-4a62-851b-7181347ce692; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-012 | cross_document_synthesis | TEST-RAG-005,TEST-RAG-002 | total=5; document=5; wiki=0 | matched=TEST-RAG-002,TEST-RAG-005; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:d607fd99-c900-4a25-951c-40a8342e3f44; chunk_id=d607fd99-c900-4a25-951c-40a8342e3f44; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-001,TEST-RAG-002,TEST-RAG-003,TEST-RAG-004,TEST-RAG-005,TEST-RAG-006,TEST-WIKI-001; evidence_id=document_chunk:67c1f837-82d8-4ed0-baef-830c1e7c1964; chunk_id=67c1f837-82d8-4ed0-baef-830c1e7c1964; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-013 | cross_document_synthesis | TEST-WIKI-001,TEST-RAG-003,TEST-RAG-004 | total=5; document=5; wiki=0 | matched=TEST-RAG-003,TEST-RAG-004,TEST-WIKI-001; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:d607fd99-c900-4a25-951c-40a8342e3f44; chunk_id=d607fd99-c900-4a25-951c-40a8342e3f44; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-003,TEST-RAG-004; evidence_id=document_chunk:1cb2ec5e-f4a3-45a6-802b-d0ca4ed3ab7d; chunk_id=1cb2ec5e-f4a3-45a6-802b-d0ca4ed3ab7d; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-014 | case_review | TEST-RAG-005 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=TEST-RAG-001,TEST-RAG-002; evidence_id=document_chunk:cf182ff0-fa01-4fc6-a100-13e55603c369; chunk_id=cf182ff0-fa01-4fc6-a100-13e55603c369; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-001,TEST-RAG-002; evidence_id=document_chunk:d78cce95-02a3-4c19-98d9-22095c090310; chunk_id=d78cce95-02a3-4c19-98d9-22095c090310; wiki_page_id=- | PARTIAL | Default top_k retrieved live evidence but missed the expected anchor or answer point. |
| P4Q-015 | case_review | TEST-RAG-006 | total=5; document=5; wiki=0 | matched=TEST-RAG-006; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:629938b3-a95f-400f-a498-145fd344faa2; chunk_id=629938b3-a95f-400f-a498-145fd344faa2; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:b9e5e04f-b28e-47bf-bcde-eaf928042ebe; chunk_id=b9e5e04f-b28e-47bf-bcde-eaf928042ebe; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-016 | case_review | TEST-RAG-005,TEST-RAG-006 | total=5; document=5; wiki=0 | matched=TEST-RAG-005,TEST-RAG-006; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:f6f24cce-d3ab-4667-a070-10fa67403a12; chunk_id=f6f24cce-d3ab-4667-a070-10fa67403a12; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-002,TEST-RAG-005,TEST-RAG-006; evidence_id=document_chunk:2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c; chunk_id=2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c; wiki_page_id=- | PARTIAL | Expected anchor appeared, but answer did not cover all required answer points or cited weak/mixed evidence. |
| P4Q-017 | wiki_retrieval | TEST-WIKI-001 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:1ad8a068-1fc3-4a24-a8a4-c3aae1b1dc1c; chunk_id=1ad8a068-1fc3-4a24-a8a4-c3aae1b1dc1c; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:9d27549f-87bd-4b0a-bb97-9f19dc683840; chunk_id=9d27549f-87bd-4b0a-bb97-9f19dc683840; wiki_page_id=- | FAIL | Wiki-only question returned document citations only; no `source_type=wiki_page` citation. |
| P4Q-018 | wiki_retrieval | TEST-WIKI-001 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:b1cb0951-e54b-4738-9dd4-5fa1dcda6b96; chunk_id=b1cb0951-e54b-4738-9dd4-5fa1dcda6b96; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:4d8918d2-49b7-481f-a89a-4a8af12254ce; chunk_id=4d8918d2-49b7-481f-a89a-4a8af12254ce; wiki_page_id=- | FAIL | Wiki-only question returned document citations only; no `source_type=wiki_page` citation. |
| P4Q-019 | wiki_retrieval | TEST-WIKI-001 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:5b9a4ee2-63b8-4860-b6b6-a7b2acac6a7d; chunk_id=5b9a4ee2-63b8-4860-b6b6-a7b2acac6a7d; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:9bb7dd77-ff1c-47d2-bfb1-9c5ef03b3832; chunk_id=9bb7dd77-ff1c-47d2-bfb1-9c5ef03b3832; wiki_page_id=- | FAIL | Wiki-only question returned document citations only; no `source_type=wiki_page` citation. |
| P4Q-020 | insufficient_evidence | none | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:293b380a-6ba0-4f97-98da-3df1df4a026b; chunk_id=293b380a-6ba0-4f97-98da-3df1df4a026b; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-001,TEST-RAG-002; evidence_id=document_chunk:de4197ac-48de-412e-afec-d43fd5910523; chunk_id=de4197ac-48de-412e-afec-d43fd5910523; wiki_page_id=- | PARTIAL | Correctly refused the unsupported real-regulator hourly-report claim, but still attached citations, so answer is PARTIAL. |
| P4Q-021 | insufficient_evidence | none | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:b82cfd43-ca5b-4394-a420-604a4a754dc5; chunk_id=b82cfd43-ca5b-4394-a420-604a4a754dc5; wiki_page_id=-<br>document_chunk; anchors=-; evidence_id=document_chunk:b1cb0951-e54b-4738-9dd4-5fa1dcda6b96; chunk_id=b1cb0951-e54b-4738-9dd4-5fa1dcda6b96; wiki_page_id=- | FAIL | Answer says no real customer can be confirmed, but wording did not contain the required insufficient-evidence cue and still cited context. |
| P4Q-022 | distractor_suppression | TEST-RAG-002 | total=5; document=5; wiki=0 | matched=TEST-RAG-002; forbidden=TEST-DISTRACTOR-001 | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=TEST-RAG-002,TEST-RAG-005,TEST-RAG-006; evidence_id=document_chunk:2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c; chunk_id=2e8cdf7b-d1eb-41a8-bcb3-ebd8c228906c; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-002,TEST-RAG-005,TEST-RAG-006; evidence_id=document_chunk:f898009f-f4d7-4634-8c72-695663aee913; chunk_id=f898009f-f4d7-4634-8c72-695663aee913; wiki_page_id=- | FAIL | Correct policy anchor appeared, but forbidden `TEST-DISTRACTOR-001` was also cited; distractor suppression failed. |
| P4Q-023 | distractor_suppression | TEST-DISTRACTOR-001 | total=5; document=5; wiki=0 | matched=-; forbidden=- | points=0; insufficient=false; source_types=document_chunk | document_chunk; anchors=-; evidence_id=document_chunk:78e8038b-9de1-4a92-9450-4c745f923564; chunk_id=78e8038b-9de1-4a92-9450-4c745f923564; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-003,TEST-RAG-004; evidence_id=document_chunk:4fd95697-0a25-485f-86c9-88d20ec31bef; chunk_id=4fd95697-0a25-485f-86c9-88d20ec31bef; wiki_page_id=- | PARTIAL | Did not retrieve the activity schedule anchor in default top_k. |
| P4Q-024 | version_conflict | TEST-RAG-001,TEST-RAG-002 | total=5; document=5; wiki=0 | matched=TEST-RAG-001,TEST-RAG-002; forbidden=- | points=0; insufficient=true; source_types=document_chunk | document_chunk; anchors=TEST-RAG-001,TEST-RAG-002; evidence_id=document_chunk:ab38a605-52de-4c35-aa4a-7a15e5fe735c; chunk_id=ab38a605-52de-4c35-aa4a-7a15e5fe735c; wiki_page_id=-<br>document_chunk; anchors=TEST-RAG-005,TEST-RAG-006; evidence_id=document_chunk:de5663fd-d44f-47a7-82da-1ef1f88d3904; chunk_id=de5663fd-d44f-47a7-82da-1ef1f88d3904; wiki_page_id=- | PARTIAL | Old/new anchors appeared, but answer remained uncertain instead of prioritizing the newer three-workday rule. |

## Key Findings

| Area | Finding | Impact |
| --- | --- | --- |
| Default retrieval isolation | The official `knowledge_qa` run did not restrict retrieval to the current P4-G2 external document set. Historical live test documents appeared in top citations. | Many document questions became PARTIAL or FAIL even though P4-G3 proved the current fixture corpus is retrievable when scoped. |
| Wiki citation | P4Q-017 to P4Q-019 returned `document_chunk` citations only. | Wiki-only QA cannot be counted as live passed. |
| Answer faithfulness | The model often refused when relevant fixture anchors appeared but snippets were weak or not answer-bearing. | This is safer than fabrication but harms useful QA. |
| Insufficient evidence | P4Q-020 refused the unsupported hourly-report claim. P4Q-021 avoided inventing a real customer name but did not clearly use the required insufficiency wording. | Refusal policy is partially effective and needs clearer prompt criteria. |
| Distractor suppression | P4Q-022 cited `TEST-DISTRACTOR-001` alongside the expected new-policy evidence. | This is a true QA failure for the distractor sentinel. |
| Version conflict | P4Q-024 cited old/new anchors but stayed uncertain instead of prioritizing the newer rule. | Version-aware answer logic needs improvement. |

## Risk Diagnosis

| Risk | Status | Notes |
| --- | --- | --- |
| Mock evidence counted as real | Controlled | Saved citations in the counted run used `source=weknora_api`; the initial sandbox network failure was discarded. |
| Current fixture evidence diluted by older data | FAIL | Default all-source top_k returned older synthetic runs and unrelated live documents. |
| Missing Wiki citation | FAIL | No P4-G5 Wiki-only question returned `source_type=wiki_page`; this matches the P4-G4 natural-language Wiki recall failure. |
| Weak evidence handling | PARTIAL | `WEAK_EVIDENCE` appeared broadly, and the model often refused instead of answering from weak snippets. |
| Citation traceability | PASS with quality risk | Citations include `evidence_id`, `source_type`, and `chunk_id`; quality still fails when the citation does not contain the answer point. |
| No-answer behavior | PARTIAL | The unsupported real-regulator question was refused; the real-customer question avoided fabrication but wording and citation policy need tightening. |

## Improvement Recommendations / 改进建议

### RAG

- Add a first-class test-run or corpus filter so `knowledge_qa` can target the current Phase 4 fixture upload without raw debug controls in the normal page.
- Improve ranking/rerank for answer-bearing chunks, not only anchor-bearing chunks; P4-G3 top_k=8 can find many anchors, but P4-G5 top_k=5 often cannot answer.
- Treat historical synthetic uploads as retrieval noise during real acceptance, or provide a cleanup / namespace strategy before QA acceptance runs.

### Wiki

- Fix natural-language Wiki retrieval for P4Q-017 to P4Q-019 before counting Wiki-only `knowledge_qa` as passed.
- Ensure `knowledge_qa` can request or preserve `source_type=wiki_page` evidence for Wiki-only questions without exposing raw debug controls to normal users.
- Keep document chunks from the Wiki seed separate from published Wiki evidence; a `TEST-WIKI-001` document citation is not a Wiki citation pass.

### QA

- Strengthen the prompt or post-checker so answers are marked incomplete when citations lack the exact answer point.
- For no-answer questions, allow refusal without attaching misleading citations, or label citations explicitly as searched-but-insufficient context.
- Add a version-conflict rule: when old and new policy evidence are both present, answer should prioritize the newer effective rule and cite both.
- Add a distractor guard that fails or removes `TEST-DISTRACTOR-001` when the user explicitly says not to use activity schedule material as policy evidence.

### Frontend

- In the knowledge QA page, display Chinese status for "引用不足", "仅检索到相似材料", and "未命中 Wiki evidence".
- Do not show low-quality citations as if they fully support the answer; distinguish "用于检索参考" from "用于结论依据".
- Keep detailed top_k/rank/source diagnostics in RAG debug, while surfacing only concise trust status in normal QA.

### Config / Ops

- Real P4-G runs that need WeKnora and chat network access should be executed outside the restricted sandbox or with approved network access; failed sandbox attempts must not be counted.
- Do not commit raw endpoints, API keys, service tokens, uploaded files, databases, logs, or unredacted provider payloads.
- Record whether each QA acceptance run uses default all-source, document-only, wiki-only, or a scoped current corpus; otherwise results are difficult to compare.
