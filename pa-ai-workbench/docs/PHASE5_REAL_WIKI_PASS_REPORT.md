# Phase 5 Real Wiki P5-G4 PASS Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P5-G4 final real Wiki closed-loop PASS gate |
| Runner | P5-C4 real Wiki closed-loop script |
| Report marker | PHASE5_REAL |
| Run id | `p5c4-33ff96d76125` |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL, service token, workspace, and default KB configured; token and endpoint intentionally omitted |
| Test scope | Phase 4 synthetic sanitized corpus `phase4_rag_wiki_qa_v1`; draft -> publish -> read -> indexed/retrievable -> Wiki-only retrieve -> citation locate; top_k=8 |
| Result | PASS |

## Closed Loop Summary

| Step | Status | Evidence |
| --- | --- | --- |
| Draft create | PASS | status=`draft`; slug=`phase5/c4-timeliness-p5c4-33ff96d76125` |
| Publish | PASS | status=`published`; source_type target=`wiki_page` |
| Read back | PASS | status=`published`; wiki_page_id=`2e8ef4ba-c93b-40ef-8341-641b52f028c6` |
| Indexed / retrievable | PASS | source_type=`wiki_page`; evidence_id=`wiki_page:2e8ef4ba-c93b-40ef-8341-641b52f028c6`; query=`TEST-WIKI-001` |
| Citation locate | PASS | target_type=`wiki_page`; ui_hash=`#/wiki?slug=phase5%2Fc4-timeliness-p5c4-33ff96d76125` |

## Wiki Evidence

| Anchor | source_type | slug | wiki_page_id | evidence_id |
| --- | --- | --- | --- | --- |
| TEST-WIKI-001 | `wiki_page` | `phase5/c4-timeliness-p5c4-33ff96d76125` | `2e8ef4ba-c93b-40ef-8341-641b52f028c6` | `wiki_page:2e8ef4ba-c93b-40ef-8341-641b52f028c6` |

## Wiki-only Question Results

| Question | Query | source | source_type | evidence_id | wiki_page_id | search_query | trace_id | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P4Q-017 | 时限管理专题中关联了哪些政策、法规和案例？ | weknora_api | wiki_page | `wiki_page:2e8ef4ba-c93b-40ef-8341-641b52f028c6` | `2e8ef4ba-c93b-40ef-8341-641b52f028c6` | 时限管理专题中关联了哪些政策、法规和案例？ | `PHASE5_REAL-P5-C4-p5c4-33ff96d76125-P4Q-017` | PASS | expected Wiki-only evidence satisfied |
| P4Q-018 | Wiki 专题指出哪些时限管理常见误区？ | weknora_api | wiki_page | `wiki_page:2e8ef4ba-c93b-40ef-8341-641b52f028c6` | `2e8ef4ba-c93b-40ef-8341-641b52f028c6` | Wiki 专题指出哪些时限管理常见误区？ | `PHASE5_REAL-P5-C4-p5c4-33ff96d76125-P4Q-018` | PASS | expected Wiki-only evidence satisfied |
| P4Q-019 | 发布后的 Wiki evidence 应该如何与原始文档 evidence 区分？ | weknora_api | wiki_page | `wiki_page:2e8ef4ba-c93b-40ef-8341-641b52f028c6` | `2e8ef4ba-c93b-40ef-8341-641b52f028c6` | 发布后的 Wiki evidence 应该如何与原始文档 evidence 区分？ | `PHASE5_REAL-P5-C4-p5c4-33ff96d76125-P4Q-019` | PASS | expected Wiki-only evidence satisfied |

## Safety Notes

- This report uses only the Phase 4 synthetic sanitized fixture corpus.
- The report intentionally omits service tokens, endpoints, uploaded file bodies, raw chunks, database contents, logs, prompts, and provider outputs.
- Evidence identifiers are recorded only to make the real WeKnora run traceable.
