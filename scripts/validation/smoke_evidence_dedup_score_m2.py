"""Fixture smoke for P3-M2-B3 evidence dedup and score display metadata."""

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

from agent.tools.citation_checker import CitationChecker  # noqa: E402
from agent.tools.real_retriever import RealRetrieverTool  # noqa: E402
from knowledge_engine.base import KnowledgeEngine  # noqa: E402
from knowledge_engine.evidence import normalize_evidence_results  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when fixture expectations fail."""


class FixtureKnowledgeBackend(KnowledgeEngine):
    def health(self) -> dict:
        return {"status": "ok", "backend": "fixture"}

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
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Evidence dedup score smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Evidence dedup score smoke passed (fixture)")
    print(f"- normalized evidence: {result['normalized_count']}")
    print(f"- agent citations: {result['citation_count']}")
    print(f"- score display: {result['score_display']}")
    print(f"- missing score display: {result['missing_score_display']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    normalized = normalize_evidence_results(_fixture_evidence(), top_k=4)
    _assert(len(normalized) == 3, f"expected 3 unique evidence items, got {len(normalized)}")
    _assert(
        [item.metadata["retrieval_rank"] for item in normalized] == [1, 2, 3],
        "display ranks should be dense after dedup",
    )
    _assert(
        normalized[0].metadata["score_display"] == "Score 1.25",
        "scored evidence display mismatch",
    )
    _assert(
        normalized[1].score is None
        and normalized[1].metadata["score_display"] == "Score unavailable",
        "missing score should not produce a precise display value",
    )

    retriever = RealRetrieverTool(
        knowledge_engine=FixtureKnowledgeBackend(),
        default_top_k=4,
    )
    citations = retriever.retrieve("fixture query", top_k=4)
    _assert(len(citations) == 3, f"expected 3 unique agent citations, got {len(citations)}")
    _assert(
        len({citation.evidence_id for citation in citations}) == 3,
        "agent citations should not duplicate evidence ids",
    )
    check = CitationChecker().validate(citations, evidence_items=citations)
    _assert(check.valid, "citation regression failed: " + "; ".join(check.warnings))
    _assert(
        citations[1].score is None
        and citations[1].metadata["score_display"] == "Score unavailable",
        "agent citation missing score display mismatch",
    )

    return {
        "normalized_count": len(normalized),
        "citation_count": len(citations),
        "score_display": normalized[0].metadata["score_display"],
        "missing_score_display": normalized[1].metadata["score_display"],
    }


def _fixture_evidence() -> list[Evidence]:
    return [
        Evidence(
            document_id=None,
            external_doc_id="wk-doc-001",
            chunk_id="chunk-001",
            title="Policy Fixture",
            text="Synthetic policy evidence one.",
            score=1.25,
            source="weknora_api",
            evidence_id="document_chunk:chunk-001",
            source_type="document_chunk",
            metadata={"score_semantics": "weknora_rrf_or_backend_score"},
        ),
        Evidence(
            document_id=None,
            external_doc_id="wk-doc-001",
            chunk_id="chunk-001",
            title="Policy Fixture Duplicate",
            text="Synthetic policy evidence duplicate.",
            score=0.99,
            source="weknora_api",
            evidence_id="document_chunk:chunk-001",
            source_type="document_chunk",
            metadata={"score_semantics": "weknora_rrf_or_backend_score"},
        ),
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            wiki_page_id="wiki-001",
            title="Wiki Fixture",
            text="Synthetic wiki evidence with no score.",
            score=None,
            source="weknora_api",
            evidence_id="wiki_page:wiki-001",
            source_type="wiki_page",
            metadata={"wiki_page_id": "wiki-001"},
        ),
        Evidence(
            document_id=None,
            external_doc_id="wk-doc-002",
            chunk_id="chunk-002",
            title="Policy Fixture Two",
            text="Synthetic policy evidence two.",
            score=0.75,
            source="weknora_api",
            source_type="document_chunk",
            metadata={},
        ),
        Evidence(
            document_id=None,
            external_doc_id="wk-doc-002",
            chunk_id="chunk-002",
            title="Policy Fixture Two Duplicate",
            text="Synthetic policy evidence two duplicate.",
            score=0.71,
            source="weknora_api",
            source_type="document_chunk",
            metadata={},
        ),
    ]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
