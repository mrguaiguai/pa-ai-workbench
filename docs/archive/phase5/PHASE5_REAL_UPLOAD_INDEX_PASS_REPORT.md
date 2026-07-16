# Phase 5 Real Upload Index PASS Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P5-G2 fresh / current-run upload and retrievability gate |
| Report marker | PHASE5_REAL |
| Date | 2026-06-16 |
| Result | PASS |
| Run id | `p5g2-bc7284a01d13` |
| Corpus id | `phase4_rag_wiki_qa_v1` |
| Namespace | `p5g2-bc7284a01d13` |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; real embedding provider preflight already passed in P5-G1; tokens and endpoints intentionally omitted |
| Scope | Phase 4 synthetic sanitized corpus; 9 fresh/current-run documents; document upload -> indexed -> anchor retrieve |

## Verdict

P5-G2 can be marked complete.

All 9 Phase 4 synthetic sanitized fixture documents were uploaded in a fresh current-run namespace, reached `indexed`, and were retrievable by their own test anchors through real WeKnora evidence.

## Current-Run Scope

```json
{
  "current_run": {
    "run_id": "p5g2-bc7284a01d13",
    "corpus_id": "phase4_rag_wiki_qa_v1",
    "namespace": "p5g2-bc7284a01d13",
    "external_doc_ids": [
      "e139f483-0735-470d-83c4-6fd7a91790c6",
      "23c03392-6251-4ebd-9009-1ad479aea013",
      "e713632c-bbc9-41e4-84b5-dfb12305af37",
      "548cae28-ac8e-48f6-990a-2f5f82048ec2",
      "72085a39-bccd-4f4e-a808-cb5e78c69098",
      "c115fd12-7b1a-46ac-b6d0-d84a7b70250f",
      "f27d8649-ea16-48f2-b8f7-4ecd6aeda928",
      "ac0df723-9736-4948-92f1-bbda074f90f7",
      "c5c14717-dd41-40c3-93fb-113beca9533c"
    ],
    "knowledge_ids": [
      "e139f483-0735-470d-83c4-6fd7a91790c6",
      "23c03392-6251-4ebd-9009-1ad479aea013",
      "e713632c-bbc9-41e4-84b5-dfb12305af37",
      "548cae28-ac8e-48f6-990a-2f5f82048ec2",
      "72085a39-bccd-4f4e-a808-cb5e78c69098",
      "c115fd12-7b1a-46ac-b6d0-d84a7b70250f",
      "f27d8649-ea16-48f2-b8f7-4ecd6aeda928",
      "ac0df723-9736-4948-92f1-bbda074f90f7",
      "c5c14717-dd41-40c3-93fb-113beca9533c"
    ],
    "anchors": [
      "TEST-DISTRACTOR-001",
      "TEST-RAG-001",
      "TEST-RAG-002",
      "TEST-RAG-003",
      "TEST-RAG-004",
      "TEST-RAG-005",
      "TEST-RAG-006",
      "TEST-RAG-007",
      "TEST-WIKI-001"
    ]
  },
  "knowledge_base_ids": ["configured-default-kb"]
}
```

## Document Evidence

| Anchor | Title | source | source_type | external_doc_id | evidence_id | chunk_id | Index status | Retrievable | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TEST-RAG-001 | 旧版专项信息报送时限政策 | `weknora_api` | `document_chunk` | `e139f483-0735-470d-83c4-6fd7a91790c6` | `document_chunk:6e2e57c6-b44d-499c-a6e3-e5400d0cda3c` | `6e2e57c6-b44d-499c-a6e3-e5400d0cda3c` | indexed | yes | PASS |
| TEST-RAG-002 | 新版专项信息报送时限政策 | `weknora_api` | `document_chunk` | `23c03392-6251-4ebd-9009-1ad479aea013` | `document_chunk:07a40fb9-3b41-48dd-b8d8-df0fbc5b4c2d` | `07a40fb9-3b41-48dd-b8d8-df0fbc5b4c2d` | indexed | yes | PASS |
| TEST-RAG-003 | 数据留存与访问审计法规条款 | `weknora_api` | `document_chunk` | `e713632c-bbc9-41e4-84b5-dfb12305af37` | `document_chunk:ed863412-0b26-46a8-8148-872c5cc909bf` | `ed863412-0b26-46a8-8148-872c5cc909bf` | indexed | yes | PASS |
| TEST-RAG-004 | 外部材料引用与发布校验法规条款 | `weknora_api` | `document_chunk` | `548cae28-ac8e-48f6-990a-2f5f82048ec2` | `document_chunk:bbb0c60c-1eaa-4dbe-95dd-b0559c75141b` | `bbb0c60c-1eaa-4dbe-95dd-b0559c75141b` | indexed | yes | PASS |
| TEST-RAG-005 | 蓝湾模拟支付延迟响应历史案例 | `weknora_api` | `document_chunk` | `72085a39-bccd-4f4e-a808-cb5e78c69098` | `document_chunk:2882184e-04d2-4515-8051-1aa463c31c6f` | `2882184e-04d2-4515-8051-1aa463c31c6f` | indexed | yes | PASS |
| TEST-RAG-006 | 北辰样例信贷信息更正历史案例 | `weknora_api` | `document_chunk` | `c115fd12-7b1a-46ac-b6d0-d84a7b70250f` | `document_chunk:72638104-3fec-4c29-84ae-fbedd9378f5a` | `72638104-3fec-4c29-84ae-fbedd9378f5a` | indexed | yes | PASS |
| TEST-RAG-007 | 资料入库、索引与问答 FAQ | `weknora_api` | `document_chunk` | `f27d8649-ea16-48f2-b8f7-4ecd6aeda928` | `document_chunk:8cda2a3c-a685-4904-8575-4ccfcc266d76` | `8cda2a3c-a685-4904-8575-4ccfcc266d76` | indexed | yes | PASS |
| TEST-WIKI-001 | 时限管理专题 Wiki 种子材料 | `weknora_api` | `document_chunk` | `ac0df723-9736-4948-92f1-bbda074f90f7` | `document_chunk:e1749a01-f2fa-4790-9304-e9713d5c9d4e` | `e1749a01-f2fa-4790-9304-e9713d5c9d4e` | indexed | yes | PASS |
| TEST-DISTRACTOR-001 | 活动排期与材料准备提醒 | `weknora_api` | `document_chunk` | `c5c14717-dd41-40c3-93fb-113beca9533c` | `document_chunk:298194cb-2fcc-46e6-bbc6-c0ab19c00014` | `298194cb-2fcc-46e6-bbc6-c0ab19c00014` | indexed | yes | PASS |

## Acceptance Summary

| Check | Result |
| --- | --- |
| Fixture contract | PASS |
| Real mode | PASS |
| 9 fixture documents uploaded | PASS |
| 9 fixture documents indexed | PASS |
| 9 fixture anchors retrievable within current-run scope | PASS |
| Historical cached material used as substitute | no |
| Mock / fixture-only evidence used as final evidence | no |

## Safety Notes

- This report uses only the Phase 4 synthetic sanitized fixture corpus.
- The report intentionally omits service tokens, endpoints, uploaded file bodies, raw chunks, database contents, logs, prompts, and provider outputs.
- Evidence identifiers are recorded only to make the real WeKnora run traceable.
