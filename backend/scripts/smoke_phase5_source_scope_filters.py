"""Fixture smoke for P5-B2 RAG source scope filtering.

This smoke proves the PA layer applies one consistent source-scope contract for
RAG service calls and Agent retrieval: document keeps document_chunk evidence,
wiki keeps wiki_page evidence, all keeps mixed evidence, and scoped empty
results emit warnings instead of silently passing.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.tools.real_retriever import RealRetrieverTool  # noqa: E402
from app.schemas import RagDebugRequest  # noqa: E402
from app.services import rag_service  # noqa: E402
from knowledge_engine.base import KnowledgeEngine  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402
from knowledge_engine.source_scope import SOURCE_SCOPE_WARNING_METADATA_KEY  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when source-scope filtering expectations fail."""


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
        if "wiki only" in query:
            return [_wiki_evidence()]
        return [_document_evidence(), _wiki_evidence(), _second_document_evidence()][:top_k]

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
        result = _run_smoke(fixture_backend)
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 source-scope filter smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        rag_service.create_knowledge_engine = original_factory  # type: ignore[assignment]

    print("Phase 5 source-scope filter smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    print(f"- document items: {result['document_items']}")
    print(f"- wiki items: {result['wiki_items']}")
    print(f"- all source types: {', '.join(result['all_source_types'])}")
    print(f"- scoped empty warnings: {result['empty_warnings']}")
    print(f"- agent wiki citations: {result['agent_wiki_citations']}")
    return 0


def _run_smoke(fixture_backend: FixtureKnowledgeBackend) -> dict[str, Any]:
    document_request = RagDebugRequest(
        query="mixed source query",
        top_k=3,
        filters={"source_scope": "document"},
    )
    _assert(document_request.filters["source_type"] == "document_chunk", "document scope did not map to source_type")
    document_result = rag_service.retrieve_evidence_with_context(
        query=document_request.query,
        filters=document_request.filters,
        top_k=document_request.top_k,
    )
    _assert({item.source_type for item in document_result.items} == {"document_chunk"}, "document scope kept non-document evidence")
    _assert(any("Source scope 'document' dropped" in warning for warning in document_result.warnings), "document scope missing mismatch warning")
    _assert(SOURCE_SCOPE_WARNING_METADATA_KEY in document_result.items[0].metadata, "document warning metadata missing")
    _assert(
        fixture_backend.calls[-1]["filters"]["source_type"] == "document_chunk",
        "document scope was not forwarded as document_chunk",
    )

    wiki_request = RagDebugRequest(
        query="mixed source query",
        top_k=3,
        filters={"source_scope": "wiki"},
    )
    _assert(wiki_request.filters["source_type"] == "wiki_page", "wiki scope did not map to source_type")
    wiki_result = rag_service.retrieve_evidence_with_context(
        query=wiki_request.query,
        filters=wiki_request.filters,
        top_k=wiki_request.top_k,
    )
    _assert({item.source_type for item in wiki_result.items} == {"wiki_page"}, "wiki scope kept non-wiki evidence")
    _assert(
        fixture_backend.calls[-1]["filters"]["source_type"] == "wiki_page",
        "wiki scope was not forwarded as wiki_page",
    )

    all_request = RagDebugRequest(
        query="mixed source query",
        top_k=3,
        filters={"source_scope": "all"},
    )
    _assert("source_type" not in all_request.filters, "all scope should not force source_type")
    all_result = rag_service.retrieve_evidence_with_context(
        query=all_request.query,
        filters=all_request.filters,
        top_k=all_request.top_k,
    )
    all_types = sorted({item.source_type for item in all_result.items})
    _assert(all_types == ["document_chunk", "wiki_page"], f"all scope did not keep mixed evidence: {all_types}")
    _assert(not all_result.warnings, "all scope should not warn on mixed document/wiki evidence")

    empty_result = rag_service.retrieve_evidence_with_context(
        query="wiki only",
        filters={"source_scope": "document"},
        top_k=3,
    )
    _assert(empty_result.items == [], "document scope should return empty when only wiki evidence exists")
    _assert(
        any("removed all retrieved evidence" in warning for warning in empty_result.warnings),
        "scoped empty result did not warn",
    )

    try:
        RagDebugRequest(query="bad", filters={"source_scope": "raw"})
    except ValidationError:
        pass
    else:
        raise SmokeError("invalid source_scope unexpectedly passed validation")
    source_type_all = RagDebugRequest(query="all", filters={"source_type": "all"})
    _assert(source_type_all.filters == {"source_scope": "all"}, "source_type=all did not normalize at schema layer")
    all_type_result = rag_service.retrieve_evidence_with_context(
        query=source_type_all.query,
        filters=source_type_all.filters,
        top_k=3,
    )
    _assert(
        "source_type" not in fixture_backend.calls[-1]["filters"],
        "source_type=all should not forward source_type to backend",
    )
    _assert(all_type_result.items, "source_type=all should keep mixed evidence")

    agent_backend = FixtureKnowledgeBackend()
    retriever = RealRetrieverTool(knowledge_engine=agent_backend, default_top_k=3)
    citations = retriever.retrieve("mixed source query", source_type="wiki", top_k=3)
    _assert(len(citations) == 1, f"expected one wiki citation, got {len(citations)}")
    _assert(citations[0].source_type == "wiki_page", "agent wiki scope kept non-wiki citation")
    _assert(
        agent_backend.calls[-1]["filters"]["source_type"] == "wiki_page",
        "agent wiki scope was not forwarded as wiki_page",
    )

    return {
        "document_items": len(document_result.items),
        "wiki_items": len(wiki_result.items),
        "all_source_types": all_types,
        "empty_warnings": len(empty_result.warnings),
        "agent_wiki_citations": len(citations),
    }


def _document_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-scope-001",
        external_doc_id="wk-doc-scope-001",
        chunk_id="chunk-scope-001",
        title="Document Scope Fixture",
        text="Synthetic document evidence for source scope filtering.",
        score=0.92,
        source="weknora_api",
        evidence_id="document_chunk:chunk-scope-001",
        source_type="document_chunk",
        metadata={},
    )


def _second_document_evidence() -> Evidence:
    return Evidence(
        document_id="pa-doc-scope-002",
        external_doc_id="wk-doc-scope-002",
        chunk_id="chunk-scope-002",
        title="Second Document Scope Fixture",
        text="Second synthetic document evidence for all-source filtering.",
        score=0.81,
        source="weknora_api",
        evidence_id="document_chunk:chunk-scope-002",
        source_type="document_chunk",
        metadata={},
    )


def _wiki_evidence() -> Evidence:
    return Evidence(
        document_id=None,
        external_doc_id=None,
        chunk_id=None,
        wiki_page_id="wiki-scope-001",
        title="Wiki Scope Fixture",
        text="Synthetic wiki evidence for source scope filtering.",
        score=0.88,
        source="weknora_api",
        evidence_id="wiki_page:wiki-scope-001",
        source_type="wiki_page",
        metadata={"wiki_page_id": "wiki-scope-001"},
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
