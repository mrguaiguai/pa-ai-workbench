"""Fixture smoke for P5-B3 answer-bearing ranking and RAG debug diagnostics."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.tools.real_retriever import RealRetrieverTool  # noqa: E402
from app.api import rag as rag_api  # noqa: E402
from app.schemas import RagDebugRequest  # noqa: E402
from app.services import rag_service  # noqa: E402
from knowledge_engine.base import KnowledgeEngine  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402


QUERY = "旧版专项信息报送政策要求普通专项信息几个工作日内完成初稿？"


class SmokeError(RuntimeError):
    """Raised when answer-bearing ranking expectations fail."""


class FixtureKnowledgeBackend(KnowledgeEngine):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def health(self) -> dict:
        return {
            "status": "ok",
            "backend": "weknora_api",
            "source": "weknora_api",
            "capabilities": {"rag_retrieve": "ready"},
        }

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        raise NotImplementedError

    def get_document_status(self, external_doc_id: str) -> dict:
        raise NotImplementedError

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        self.calls.append({"query": query, "filters": filters or {}, "top_k": top_k})
        return [_broad_evidence(), _answer_evidence(), _weak_evidence()][:top_k]

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        raise NotImplementedError

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        raise NotImplementedError


def main() -> int:
    original_factory = rag_service.create_knowledge_engine
    fixture_backend = FixtureKnowledgeBackend()
    rag_service.create_knowledge_engine = lambda: fixture_backend  # type: ignore[assignment]
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 answer-bearing ranking smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        rag_service.create_knowledge_engine = original_factory  # type: ignore[assignment]

    print("Phase 5 answer-bearing ranking smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    print(f"- top evidence id: {result['top_evidence_id']}")
    print(f"- raw rank -> answer rank: {result['raw_rank']} -> {result['answer_rank']}")
    print(f"- matched terms: {', '.join(result['matched_terms'][:5])}")
    print(f"- debug score semantics: {result['score_semantics']}")
    print(f"- agent top citation id: {result['agent_top_citation_id']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    service_result = rag_service.retrieve_evidence_with_context(
        query=QUERY,
        filters={"source_scope": "document"},
        top_k=2,
    )
    _assert(service_result.items, "service returned no ranked evidence")
    top = service_result.items[0]
    _assert(top.evidence_id == "document_chunk:chunk-answer", "answer-bearing chunk was not promoted")
    _assert(top.metadata.get("answer_bearing_raw_rank") == 2, "raw answer rank should be preserved")
    _assert(top.metadata.get("answer_bearing_rank") == 1, "answer rank should be first")
    _assert(top.metadata.get("answer_bearing_rank_delta") == 1, "rank delta should show promotion")
    matched_terms = top.metadata.get("answer_bearing_matched_terms") or []
    _assert(any("工作日" in term or "初稿" in term for term in matched_terms), "missing useful matched query terms")
    _assert(top.metadata.get("retrieval_rank") == 1, "normalized retrieval rank should be first after rerank")
    _assert(top.metadata.get("raw_retrieval_rank") == 1, "raw retrieval rank should describe post-rerank normalized input")

    debug_response = rag_api.retrieve_rag_debug(
        RagDebugRequest(query=QUERY, top_k=2, filters={"source_scope": "document"})
    )
    debug_payload = debug_response.model_dump()
    _assert(debug_payload["status"] == "ok", "debug response should be ok")
    debug_top = debug_payload["items"][0]
    _assert(debug_top["evidence_id"] == "document_chunk:chunk-answer", "debug top item mismatch")
    debug_metadata = debug_top["metadata"]
    for key in (
        "answer_bearing_score",
        "answer_bearing_matched_terms",
        "answer_bearing_raw_rank",
        "answer_bearing_rank",
        "score_semantics",
        "retrieval_rank",
    ):
        _assert(key in debug_metadata, f"debug metadata missing {key}")

    agent_backend = FixtureKnowledgeBackend()
    citations = RealRetrieverTool(
        knowledge_engine=agent_backend,
        default_top_k=2,
    ).retrieve(QUERY, filters={"source_scope": "document"}, top_k=2)
    _assert(citations[0].evidence_id == "document_chunk:chunk-answer", "agent top citation was not reranked")
    _assert("answer_bearing_score" in citations[0].metadata, "agent citation missing ranking diagnostics")

    return {
        "top_evidence_id": top.evidence_id,
        "raw_rank": top.metadata["answer_bearing_raw_rank"],
        "answer_rank": top.metadata["answer_bearing_rank"],
        "matched_terms": matched_terms,
        "score_semantics": debug_metadata["score_semantics"],
        "agent_top_citation_id": citations[0].evidence_id,
    }


def _broad_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-old-policy",
        external_doc_id="wk-doc-old-policy",
        chunk_id="chunk-broad",
        title="旧版专项信息报送政策概览",
        text="本段介绍旧版专项信息报送政策的背景、适用范围和流程角色，但没有给出普通事项初稿时限。",
        score=0.99,
        source="weknora_api",
        evidence_id="document_chunk:chunk-broad",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-001"},
    )


def _answer_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-old-policy",
        external_doc_id="wk-doc-old-policy",
        chunk_id="chunk-answer",
        title="旧版专项信息报送时限",
        text="TEST-RAG-001：旧版政策要求普通专项信息应在五个工作日内完成初稿，跨部门口径可延长至七个工作日。",
        score=0.51,
        source="weknora_api",
        evidence_id="document_chunk:chunk-answer",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-001"},
    )


def _weak_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-new-policy",
        external_doc_id="wk-doc-new-policy",
        chunk_id="chunk-weak",
        title="新版政策背景",
        text="新版政策强调资料来源边界和风险分级。",
        score=0.49,
        source="weknora_api",
        evidence_id="document_chunk:chunk-weak",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-002"},
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
