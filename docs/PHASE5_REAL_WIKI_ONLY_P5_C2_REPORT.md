# Phase 5 P5-C2 Real Wiki-only Retrieval Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P5-C2 Wiki-only natural-language retrieval |
| Report marker | PHASE5_REAL |
| Run id | `p5c2-4f415c817f2f` |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL, service token, workspace, and default KB configured; token and endpoint intentionally omitted |
| Test scope | Phase 4 synthetic sanitized corpus `phase4_rag_wiki_qa_v1`; P4Q-017 to P4Q-019; top_k=8; fresh/current-run Wiki page |
| Result | PASS |

## Summary

| Status | Count |
| --- | ---: |
| PASS | 3 |
| FAIL | 0 |

## Current-Run Wiki Evidence

| Anchor | source_type | slug | wiki_page_id | evidence_id |
| --- | --- | --- | --- | --- |
| TEST-WIKI-001 | `wiki_page` | `phase5/c2-timeliness-p5c2-4f415c817f2f` | `7c7defea-6e19-4b76-86d2-7e9bb7e55621` | `wiki_page:7c7defea-6e19-4b76-86d2-7e9bb7e55621` |

## Wiki-only Question Results

| Question | Query | source | source_type | evidence_id | wiki_page_id | search_query | trace_id | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P4Q-017 | 时限管理专题中关联了哪些政策、法规和案例？ | weknora_api | wiki_page | `wiki_page:7c7defea-6e19-4b76-86d2-7e9bb7e55621` | `7c7defea-6e19-4b76-86d2-7e9bb7e55621` | 时限管理专题中关联了哪些政策、法规和案例？ | `PHASE5_REAL-P5-C2-p5c2-4f415c817f2f-P4Q-017` | PASS | expected Wiki-only evidence satisfied |
| P4Q-018 | Wiki 专题指出哪些时限管理常见误区？ | weknora_api | wiki_page | `wiki_page:7c7defea-6e19-4b76-86d2-7e9bb7e55621` | `7c7defea-6e19-4b76-86d2-7e9bb7e55621` | Wiki 专题指出哪些时限管理常见误区？ | `PHASE5_REAL-P5-C2-p5c2-4f415c817f2f-P4Q-018` | PASS | expected Wiki-only evidence satisfied |
| P4Q-019 | 发布后的 Wiki evidence 应该如何与原始文档 evidence 区分？ | weknora_api | wiki_page | `wiki_page:7c7defea-6e19-4b76-86d2-7e9bb7e55621` | `7c7defea-6e19-4b76-86d2-7e9bb7e55621` | 发布后的 Wiki evidence 应该如何与原始文档 evidence 区分？ | `PHASE5_REAL-P5-C2-p5c2-4f415c817f2f-P4Q-019` | PASS | expected Wiki-only evidence satisfied |

## Safety Notes

- This report uses only the Phase 4 synthetic sanitized fixture corpus.
- The report intentionally omits service tokens, endpoints, uploaded file bodies, raw chunks, database contents, logs, prompts, and provider outputs.
- Evidence identifiers are recorded only to make the real WeKnora run traceable.
