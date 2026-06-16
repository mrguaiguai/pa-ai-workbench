# Phase 5 Real Frontend PASS Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P5-E4 frontend build and browser acceptance |
| Report id | PHASE5_REAL_FRONTEND_PASS_REPORT |
| Test date | 2026-06-16 CST |
| Environment | Local PA backend on `127.0.0.1:8000`; Vite frontend on `127.0.0.1:5173`; Codex in-app Browser |
| Backend mode | `KNOWLEDGE_BACKEND=weknora_api`; `MOCK_MODE=false` |
| Result | PASS |

## Validation Summary

| Check | Result | Evidence |
| --- | --- | --- |
| TypeScript | PASS | Bundled Node equivalent of `tsc --noEmit` completed successfully. |
| Frontend build | PASS | Bundled Node equivalent of `vite build` completed successfully and generated `frontend/dist`. |
| Backend compile | PASS | `backend/.venv/bin/python -m compileall backend/app` completed successfully. |
| Backend status smoke | PASS | HTTP `/api/status` returned `knowledge_backend=weknora_api`, `mock_mode=false`, `weknora.status=connected`, `health_status=ok`. |
| Real status display | PASS | Browser showed WeKnora as connected, chat model as real, embedding model as mock, and RAG as fallback because embedding is mock. |
| Browser acceptance | PASS | In-app Browser opened all six required pages and found required visible text with no blocking console errors. |
| English residual scan | PASS | Browser scan found no blocking residuals such as `Chat Model`, `RAG Pipeline`, `Mock fallback`, `Real WeKnora RAG`, `Score unavailable`, or the old document readiness sentence. |

## Runtime Status Evidence

| Signal | Observed value | Frontend implication |
| --- | --- | --- |
| Knowledge backend | `weknora_api` | Frontend must show WeKnora-backed mode. |
| Mock mode | `False` | Frontend must not label backend as mock. |
| WeKnora health | `connected`; `health_status=ok` | Frontend can show WeKnora-backed capability as connected. |
| Model status | chat provider real; embedding provider `mock`; model mock mode `False` | Frontend must show mixed model status and avoid treating embedding as real. |
| Capability counts | `supported=11`, `partial=0`, `unsupported=0` | Capability card can show real available state for this smoke. |

## Browser Page Matrix

| Page | Route | Required visible evidence | Result |
| --- | --- | --- | --- |
| 首页 | `#/` | `工作台首页`, `资料库`, `RAG 调试`, `对话模型`, `RAG 检索链路`, `能力边界` | PASS |
| 资料库 | `#/library` | `资料库`, `上传`, `资料列表`, `分块`, `文档已索引，可用于有依据回答。` | PASS |
| RAG 调试 | `#/rag-debug` | `RAG 检索调试`, `检索问题`, `返回数量（Top K）`, `检索来源`, `运行` | PASS |
| Wiki | `#/wiki` | `Wiki 知识库`, `搜索`, `页面`, `索引`, `可检索` | PASS |
| 知识问答 | `#/analysis` | `智能分析台`, `知识问答`, `知识来源`, `全部知识`, `仅文档`, `仅 Wiki`, `证据` | PASS |
| 历史 | `#/history` | `生成历史`, `筛选`, `结果列表`, `引用来源`, `证据状态` | PASS |

## Screenshot Evidence

Screenshots were captured in the local temporary directory for this acceptance run:

| Page | Screenshot |
| --- | --- |
| 首页 | `/private/tmp/p5-e4-frontend-screens/home.png` |
| 资料库 | `/private/tmp/p5-e4-frontend-screens/library.png` |
| RAG 调试 | `/private/tmp/p5-e4-frontend-screens/rag-debug.png` |
| Wiki | `/private/tmp/p5-e4-frontend-screens/wiki.png` |
| 知识问答 | `/private/tmp/p5-e4-frontend-screens/analysis.png` |
| 历史 | `/private/tmp/p5-e4-frontend-screens/history.png` |

The screenshots are not committed because they are generated runtime artifacts and the visible local data may include environment-specific record titles. This report records only sanitized page-level evidence.

## Fix Applied During P5-E4

The browser pass found one blocking English residual in the document readiness display:

```text
Document is indexed and ready for grounded answers.
```

The frontend display layer now maps that backend message to:

```text
文档已索引，可用于有依据回答。
```

The raw API value remains unchanged; only the user-facing display is localized.

## Final Result

P5-E4 PASS.

The frontend builds successfully, all required core pages render in a real local browser session, no blocking English residual from the Phase 4 frontend report remains in the checked views, and runtime status display does not hide mock embedding behind a fully real ready label.
