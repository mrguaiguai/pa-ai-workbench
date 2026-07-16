"""Fixture smoke for P5-B1 current-run corpus isolation.

The smoke simulates a backend that returns current and historical evidence even
when scoped filters are supplied. PA must still drop out-of-scope evidence and
emit a warning so Phase 5 acceptance cannot accidentally pass with old live data.
"""

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
from app.schemas import RagDebugRequest  # noqa: E402
from app.services import rag_service  # noqa: E402
from knowledge_engine.base import KnowledgeEngine  # noqa: E402
from knowledge_engine.current_run import CURRENT_RUN_FILTER_KEY  # noqa: E402
from knowledge_engine.current_run import CURRENT_RUN_WARNING_METADATA_KEY  # noqa: E402
from knowledge_engine.current_run import apply_current_run_isolation  # noqa: E402
from knowledge_engine.current_run import prepare_current_run_filters  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402


CURRENT_RUN_FILTER = {
    "run_id": "phase5-smoke-run-001",
    "corpus_id": "phase4_rag_wiki_qa_v1",
    "document_ids": ["pa-doc-current-001"],
    "external_doc_ids": ["wk-current-001"],
    "anchors": ["TEST-RAG-001"],
}


class SmokeError(RuntimeError):
    """Raised when current-run isolation expectations fail."""


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
        return _fixture_evidence()[:top_k]

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
        print(f"Phase 5 current-run isolation smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        rag_service.create_knowledge_engine = original_factory  # type: ignore[assignment]

    print("Phase 5 current-run isolation smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    print(f"- service items kept: {result['service_items_kept']}")
    print(f"- agent citations kept: {result['agent_citations_kept']}")
    print(f"- wiki page evidence kept: {result['wiki_items_kept']}")
    print(f"- wiki page evidence dropped: {result['wiki_items_dropped']}")
    print(f"- dropped evidence warning: {result['dropped_warning']}")
    print(f"- backend knowledge ids: {', '.join(result['backend_knowledge_ids'])}")
    return 0


def _run_smoke(fixture_backend: FixtureKnowledgeBackend) -> dict[str, Any]:
    request = RagDebugRequest(
        query="current policy deadline",
        top_k=2,
        filters={CURRENT_RUN_FILTER_KEY: CURRENT_RUN_FILTER},
    )
    _assert(
        request.filters[CURRENT_RUN_FILTER_KEY]["external_doc_ids"] == ["wk-current-001"],
        "RAG schema did not preserve current_run external ids",
    )

    result = rag_service.retrieve_evidence_with_context(
        query=request.query,
        filters=request.filters,
        top_k=request.top_k,
    )
    _assert(len(result.items) == 1, f"expected only current evidence, got {len(result.items)}")
    current = result.items[0]
    _assert(current.external_doc_id == "wk-current-001", "historical evidence was not filtered")
    _assert(current.metadata.get("current_run_isolated") is True, "current-run metadata missing")
    _assert(
        CURRENT_RUN_WARNING_METADATA_KEY in current.metadata,
        "current-run warning metadata missing",
    )
    _assert(
        any("dropped 2 evidence" in warning for warning in result.warnings),
        "missing dropped-evidence warning",
    )
    _assert(fixture_backend.calls, "backend retrieve was not called")
    service_call = fixture_backend.calls[-1]
    _assert(
        service_call["filters"]["knowledge_ids"] == ["wk-current-001"],
        "current external ids were not forwarded as backend knowledge_ids",
    )
    _assert(
        service_call["top_k"] >= request.top_k + 8,
        "current-run retrieval should overfetch before PA-side filtering",
    )

    agent_backend = FixtureKnowledgeBackend()
    retriever = RealRetrieverTool(knowledge_engine=agent_backend, default_top_k=2)
    citations = retriever.retrieve(
        "current policy deadline",
        filters={CURRENT_RUN_FILTER_KEY: CURRENT_RUN_FILTER},
        top_k=2,
    )
    _assert(len(citations) == 1, f"expected one current citation, got {len(citations)}")
    _assert(citations[0].external_doc_id == "wk-current-001", "agent kept historical citation")
    _assert(
        CURRENT_RUN_WARNING_METADATA_KEY in citations[0].metadata,
        "agent citation did not preserve current-run warning metadata",
    )
    _assert(
        agent_backend.calls[-1]["filters"]["knowledge_ids"] == ["wk-current-001"],
        "agent retriever did not forward backend knowledge_ids",
    )

    wiki_scope_filter = {
        **CURRENT_RUN_FILTER,
        "wiki_page_ids": ["wiki-current-001", "phase5/current-wiki"],
    }
    prepared = prepare_current_run_filters({CURRENT_RUN_FILTER_KEY: wiki_scope_filter})
    isolated = apply_current_run_isolation(_wiki_fixture_evidence(), prepared.scope)
    _assert(
        [item.wiki_page_id for item in isolated.items] == ["wiki-current-001"],
        "explicit current-run wiki_page_ids did not filter historical wiki evidence",
    )
    _assert(isolated.dropped_count == 1, "historical wiki evidence was not dropped")

    return {
        "service_items_kept": len(result.items),
        "agent_citations_kept": len(citations),
        "wiki_items_kept": len(isolated.items),
        "wiki_items_dropped": isolated.dropped_count,
        "dropped_warning": next(
            warning for warning in result.warnings if "dropped 2 evidence" in warning
        ),
        "backend_knowledge_ids": service_call["filters"]["knowledge_ids"],
    }


def _fixture_evidence() -> list[Evidence]:
    return [
        Evidence(
            document_id="pa-doc-current-001",
            external_doc_id="wk-current-001",
            chunk_id="chunk-current-001",
            title="Current Phase 5 Fixture",
            text="TEST-RAG-001 current-run evidence for the Phase 5 fixture corpus.",
            score=0.91,
            source="weknora_api",
            evidence_id="document_chunk:chunk-current-001",
            source_type="document_chunk",
            metadata={
                "anchor": "TEST-RAG-001",
                "corpus_id": "phase4_rag_wiki_qa_v1",
            },
        ),
        Evidence(
            document_id="pa-doc-old-001",
            external_doc_id="wk-old-001",
            chunk_id="chunk-old-001",
            title="Historical Upload Fixture",
            text="TEST-RAG-001 historical evidence from an older upload.",
            score=0.88,
            source="weknora_api",
            evidence_id="document_chunk:chunk-old-001",
            source_type="document_chunk",
            metadata={"anchor": "TEST-RAG-001"},
        ),
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id="chunk-unbound-001",
            title="Unbound Fixture",
            text="Unbound evidence without current-run identifiers.",
            score=0.77,
            source="weknora_api",
            evidence_id="document_chunk:chunk-unbound-001",
            source_type="document_chunk",
            metadata={},
        ),
    ]


def _wiki_fixture_evidence() -> list[Evidence]:
    return [
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            wiki_page_id="wiki-current-001",
            title="Current Phase 5 Wiki Fixture",
            text="TEST-RAG-001 current-run Wiki evidence for the Phase 5 fixture corpus.",
            score=0.93,
            source="weknora_api",
            evidence_id="wiki_page:wiki-current-001",
            source_type="wiki_page",
            metadata={
                "anchor": "TEST-RAG-001",
                "slug": "phase5/current-wiki",
                "corpus_id": "phase4_rag_wiki_qa_v1",
            },
        ),
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            wiki_page_id="wiki-old-001",
            title="Historical Phase 5 Wiki Fixture",
            text="TEST-RAG-001 historical Wiki evidence with the same anchor.",
            score=0.9,
            source="weknora_api",
            evidence_id="wiki_page:wiki-old-001",
            source_type="wiki_page",
            metadata={
                "anchor": "TEST-RAG-001",
                "slug": "phase5/old-wiki",
            },
        ),
    ]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
