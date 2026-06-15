# Phase 4 Real Wiki Closed-Loop Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G4 Wiki draft, publish, retrieve, and citation traceability real test |
| Test time | 2026-06-15 17:00:56 CST |
| Test environment | Local PA AI Workbench CLI using PA `WeKnoraApiBackend` adapter |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL configured; service token configured; workspace configured; default KB configured; token and endpoint intentionally omitted |
| Test scope | `TEST-WIKI-001` synthetic sanitized Wiki seed; draft -> published -> read -> Wiki-only retrieve |
| Wiki slug | `phase4/p4g4-timeliness-p4g4-20260615165637-bc0fe0bd` |
| Wiki page id / wiki_page_id | `c25e8000-6979-468f-afdf-3952b57c4903` |
| Trace id / trace_id | `p4g4-b27b9f6a6263` |
| Test result / 测试结果 | PARTIAL / 部分通过 |

## Summary

| Step | Result | Evidence |
| --- | --- | --- |
| Draft create | PASS | Draft page returned `source=weknora_api`, slug matched, status was `draft` |
| Publish | PASS | Published page returned `source=weknora_api`, same slug, status was `published` |
| Read back | PASS | `read_wiki_page(slug)` returned the published page and metadata for `TEST-WIKI-001` |
| Targeted Wiki-only retrieve | PASS | Queries using `TEST-WIKI-001`, title, or slug returned `source_type=wiki_page` evidence for the current page |
| Official Wiki question retrieve | FAIL | P4Q-017, P4Q-018, and P4Q-019 returned 0 Wiki evidence items |
| Citation traceability | PASS with risk | Retrieved targeted evidence includes `evidence_id=wiki_page:c25e8000-6979-468f-afdf-3952b57c4903`, `wiki_page_id=c25e8000-6979-468f-afdf-3952b57c4903`, source refs, and chunk refs |

The Wiki closed loop is partially usable: the page can be created, published, read, and retrieved by anchor / title / slug as `wiki_page` evidence, but natural-language Wiki questions do not retrieve it yet. Therefore P4-G4 is not a full live PASS.

## Source Material

| Field | Value |
| --- | --- |
| Fixture anchor | TEST-WIKI-001 |
| Fixture file | `backend/fixtures/phase4_rag_wiki_qa/documents/008_timeliness_wiki_seed.md` |
| Source document external_doc_id | `e560bf34-8487-4603-ac0e-77ac8193ddc0` |
| Source document evidence_id | `document_chunk:67c1f837-82d8-4ed0-baef-830c1e7c1964` |
| Source document chunk_id | `67c1f837-82d8-4ed0-baef-830c1e7c1964` |

## Draft And Publish Evidence

| State | Source | Slug | Status | Version | Notes |
| --- | --- | --- | --- | --- | --- |
| draft | `weknora_api` | `phase4/p4g4-timeliness-p4g4-20260615165637-bc0fe0bd` | draft | 1 | Page was created from synthetic TEST-WIKI-001 seed content |
| published | `weknora_api` | `phase4/p4g4-timeliness-p4g4-20260615165637-bc0fe0bd` | published | 2 | Same page was updated to published |

## Retrieve Evidence

| Query | Count | Current page matched | source_type | Evidence |
| --- | ---: | --- | --- | --- |
| `TEST-WIKI-001` | 3 | yes | `source_type=wiki_page` | `evidence_id=wiki_page:c25e8000-6979-468f-afdf-3952b57c4903`; `wiki_page_id=c25e8000-6979-468f-afdf-3952b57c4903` |
| `时限管理专题 Wiki` | 2 | yes | `source_type=wiki_page` | `evidence_id=wiki_page:c25e8000-6979-468f-afdf-3952b57c4903`; `wiki_page_id=c25e8000-6979-468f-afdf-3952b57c4903` |
| `source_type=wiki_page` | 5 | yes | `source_type=wiki_page` | Current page appeared behind another Wiki page |
| `phase4/p4g4-timeliness-p4g4-20260615165637-bc0fe0bd` | 1 | yes | `source_type=wiki_page` | Direct slug query returned the current page |
| `旧版五个工作日 新版三个工作日 Wiki 发布后检索` | 0 | no | none | Natural-language concept query failed |

## Official Wiki Question Results

| Question | Query | Result | Evidence |
| --- | --- | --- | --- |
| P4Q-017 | 时限管理专题中关联了哪些政策、法规和案例？ | FAIL | 0 Wiki evidence items; trace_id=`p4g4-17d1912c92e4` |
| P4Q-018 | Wiki 专题指出哪些时限管理常见误区？ | FAIL | 0 Wiki evidence items; trace_id=`p4g4-49ae832839e6` |
| P4Q-019 | 发布后的 Wiki evidence 应该如何与原始文档 evidence 区分？ | FAIL | 0 Wiki evidence items; trace_id=`p4g4-0ca6ce775194` |

## Citation Traceability

The targeted Wiki retrieve result for the current page includes:

- `source=weknora_api`
- `source_type=wiki_page`
- `evidence_id=wiki_page:c25e8000-6979-468f-afdf-3952b57c4903`
- `wiki_page_id=c25e8000-6979-468f-afdf-3952b57c4903`
- `weknora_wiki_page_slug=phase4/p4g4-timeliness-p4g4-20260615165637-bc0fe0bd`
- source ref to the P4-G2 `TEST-WIKI-001` source document
- chunk ref to `67c1f837-82d8-4ed0-baef-830c1e7c1964`

This is enough to prove citation traceability for targeted Wiki evidence, but not enough to prove the official P4Q Wiki questions pass.

## Risk Diagnosis

| Risk | Status | Notes |
| --- | --- | --- |
| Published but not retrievable | Partly controlled | Page is retrievable by anchor/title/slug, but not by official natural-language Wiki questions |
| Wiki question recall | FAIL | P4Q-017 to P4Q-019 all returned 0 Wiki evidence |
| Source-type traceability | PASS | Targeted results return `source_type=wiki_page`, `wiki_page_id`, and `evidence_id` |
| Stale or unrelated Wiki pages | Needs attention | Some targeted queries also returned automatically generated summary/entity Wiki pages from P4-G2 uploads |
| QA readiness | Not complete | P4-G5 must not treat P4Q-017 to P4Q-019 as live-passed until Wiki question recall improves |

## Improvement Recommendations / 改进建议

### RAG

- Re-run P4Q-017 to P4Q-019 after tuning Wiki search query construction or indexing fields; current natural-language recall is insufficient.
- Add a diagnostic mode that reports whether Wiki search matched by title, slug, content, summary, alias, or source_refs.
- Consider adding aliases or search keywords derived from TEST-WIKI-001, such as “关联政策”, “常见误区”, and “Wiki evidence 区分”.

### Wiki

- Ensure published Wiki content, summary, aliases, and metadata fields are all included in the WeKnora Wiki search index.
- Add explicit post-publish reindex / refresh status if available; P4-G4 currently sees published + targeted retrievable, but official question recall fails.
- Distinguish user-created P4-G4 Wiki pages from automatically generated summary/entity pages when displaying Wiki evidence.

### QA

- P4-G5 should mark P4Q-017 to P4Q-019 as failed or blocked unless `knowledge_qa` can retrieve real `wiki_page` evidence for those natural-language questions.
- `knowledge_qa` should not fall back to document chunks and claim Wiki citation success for Wiki-only questions.

### Frontend

- The Wiki page should show separate states for “published”, “retrievable by direct query”, and “retrievable by expected test question”.
- RAG debug should show `wiki_page_id`, slug, and whether the matched page is the current test page.

### Config / Ops

- Do not commit raw endpoints, service tokens, uploaded files, databases, logs, or unredacted response bodies.
- Keep P4-G4 reports tied to the current slug and `wiki_page_id`; future retests should create a new slug or explicitly record that they reuse this page.
