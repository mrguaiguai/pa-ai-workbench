"""Fixture smoke for P5-B4 TEST-DISTRACTOR-001 regression guard."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.tools.real_retriever import RealRetrieverTool  # noqa: E402
from app.api import rag as rag_api  # noqa: E402
from app.schemas import RagDebugRequest  # noqa: E402
from app.services import rag_service  # noqa: E402
from knowledge_engine.base import KnowledgeEngine  # noqa: E402
from knowledge_engine.distractor_guard import DISTRACTOR_ANCHOR  # noqa: E402
from knowledge_engine.distractor_guard import DISTRACTOR_WARNING_METADATA_KEY  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402


POLICY_QUERY = "新版专项信息政策要求普通事项几个工作日内完成初稿？不要把活动排版日期当成依据。"
ACTIVITY_QUERY = "如果问题只涉及活动讲师和排版安排，应命中哪份材料？这是否能作为政策时限依据？"


class SmokeError(RuntimeError):
    """Raised when distractor guard expectations fail."""


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
        if "活动讲师" in query or "排版安排" in query:
            return [_distractor_evidence(), _policy_evidence()][:top_k]
        return [_distractor_evidence(), _policy_evidence(), _old_policy_evidence()][:top_k]

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
        print(f"Phase 5 distractor guard smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        rag_service.create_knowledge_engine = original_factory  # type: ignore[assignment]

    print("Phase 5 distractor guard smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    print(f"- policy result anchors: {', '.join(result['policy_anchors'])}")
    print(f"- activity result anchors: {', '.join(result['activity_anchors'])}")
    print(f"- policy warnings: {result['policy_warning_count']}")
    print(f"- agent policy citations: {result['agent_policy_citations']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    policy_result = rag_service.retrieve_evidence_with_context(
        query=POLICY_QUERY,
        filters={"source_scope": "all"},
        top_k=3,
    )
    policy_anchors = _anchors(policy_result.items)
    _assert(DISTRACTOR_ANCHOR not in policy_anchors, "policy query kept TEST-DISTRACTOR-001")
    _assert("TEST-RAG-002" in policy_anchors, "policy query lost the expected new-policy evidence")
    _assert(any("Distractor guard dropped" in warning for warning in policy_result.warnings), "policy query missing distractor warning")
    _assert(
        any(DISTRACTOR_WARNING_METADATA_KEY in item.metadata for item in policy_result.items),
        "policy kept evidence missing distractor warning metadata",
    )

    debug_response = rag_api.retrieve_rag_debug(
        RagDebugRequest(query=POLICY_QUERY, top_k=3, filters={"source_scope": "all"})
    )
    debug_payload = debug_response.model_dump()
    debug_anchors = [
        item["metadata"].get("anchor")
        for item in debug_payload["items"]
        if item["metadata"].get("anchor")
    ]
    _assert(DISTRACTOR_ANCHOR not in debug_anchors, "debug response kept distractor for policy query")
    _assert(debug_payload["warnings"], "debug response missing distractor warnings")

    activity_result = rag_service.retrieve_evidence_with_context(
        query=ACTIVITY_QUERY,
        filters={"source_scope": "document"},
        top_k=3,
    )
    activity_anchors = _anchors(activity_result.items)
    _assert(DISTRACTOR_ANCHOR in activity_anchors, "activity query did not keep the distractor material")
    distractor = next(item for item in activity_result.items if _anchor(item) == DISTRACTOR_ANCHOR)
    _assert(
        distractor.metadata.get("distractor_guard_decision") == "allowed_activity_context",
        "activity distractor decision metadata mismatch",
    )

    agent_backend = FixtureKnowledgeBackend()
    citations = RealRetrieverTool(knowledge_engine=agent_backend, default_top_k=3).retrieve(
        POLICY_QUERY,
        filters={"source_scope": "all"},
        top_k=3,
    )
    agent_anchors = [
        str(citation.metadata.get("anchor") or "")
        for citation in citations
        if citation.metadata.get("anchor")
    ]
    _assert(DISTRACTOR_ANCHOR not in agent_anchors, "agent policy citations kept distractor")

    return {
        "policy_anchors": policy_anchors,
        "activity_anchors": activity_anchors,
        "policy_warning_count": len(policy_result.warnings),
        "agent_policy_citations": len(citations),
    }


def _anchors(items: list[Evidence]) -> list[str]:
    return [anchor for anchor in (_anchor(item) for item in items) if anchor]


def _anchor(item: Evidence) -> str:
    return str(item.metadata.get("anchor") or "")


def _policy_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-new-policy",
        external_doc_id="wk-doc-new-policy",
        chunk_id="chunk-new-policy",
        title="新版专项信息报送时限政策",
        text="TEST-RAG-002：新版政策要求普通专项信息三个工作日内完成初稿，第四个工作日前完成复核。",
        score=0.87,
        source="weknora_api",
        evidence_id="document_chunk:chunk-new-policy",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-002"},
    )


def _old_policy_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-old-policy",
        external_doc_id="wk-doc-old-policy",
        chunk_id="chunk-old-policy",
        title="旧版专项信息报送时限政策",
        text="TEST-RAG-001：旧版政策要求普通专项信息五个工作日内完成初稿。",
        score=0.61,
        source="weknora_api",
        evidence_id="document_chunk:chunk-old-policy",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-001"},
    )


def _distractor_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-distractor",
        external_doc_id="wk-doc-distractor",
        chunk_id="chunk-distractor",
        title="活动排期与材料准备提醒",
        text="TEST-DISTRACTOR-001：培训演示材料在 2025-04-03 完成排版，活动讲师使用该材料进行演示。",
        score=0.96,
        source="weknora_api",
        evidence_id="document_chunk:chunk-distractor",
        source_type="document_chunk",
        metadata={"anchor": DISTRACTOR_ANCHOR},
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
