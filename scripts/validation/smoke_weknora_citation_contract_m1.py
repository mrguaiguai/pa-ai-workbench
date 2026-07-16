"""Contract-check WeKnora Evidence -> Citation traceability.

This fixture test covers P3-M1-B4 and WF-P0-05:
- document_chunk evidence can become a traceable citation.
- wiki_page evidence can become a traceable citation through metadata binding.
- persisted citations can be located through PA document/Wiki routes.
- incomplete non-mock evidence fails closed.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.schemas import Citation as AgentCitation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from app.services.generation_service import create_output_with_citations  # noqa: E402
from app.services.generation_service import create_task  # noqa: E402
from app.models import Document  # noqa: E402
from app.models import DocumentChunk  # noqa: E402
from app.models import WikiPage  # noqa: E402
from app.schemas import CitationLocateRequest  # noqa: E402
from app.services.citation_locator_service import locate_citation  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.citations import CitationBuilder  # noqa: E402
from knowledge_engine.citations import CitationBindingError  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the citation contract fails."""


def main() -> int:
    try:
        result = _run_contract_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora citation contract smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora citation contract smoke passed (fixture)")
    print(f"- document evidence id: {result['document_evidence_id']}")
    print(f"- wiki evidence id: {result['wiki_evidence_id']}")
    print(f"- saved citations: {result['saved_citations']}")
    print(f"- located citations: {result['located_citations']}")
    print(f"- fail-closed checks: {result['fail_closed_checks']}")
    return 0


def _run_contract_smoke() -> dict[str, Any]:
    builder = CitationBuilder()
    document_evidence = builder.build(
        WeKnoraApiBackend._to_evidence(
            {
                "id": "chunk-policy-001",
                "content": "sanitized policy evidence",
                "knowledge_id": "wk-doc-001",
                "knowledge_base_id": "kb-default",
                "knowledge_title": "Fixture Policy",
                "chunk_index": 2,
                "start_at": 8,
                "end_at": 34,
                "score": 1.7,
                "match_type": 2,
                "chunk_type": "text",
            }
        )
    )
    wiki_evidence = builder.build(
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            wiki_page_id="wiki-page-001",
            evidence_id=None,
            source_type="wiki_page",
            title="Fixture Wiki",
            text="sanitized wiki evidence",
            score=2.3,
            source="weknora_api",
            metadata={
                "wiki_page_id": "wiki-page-001",
                "slug": "fixture-wiki",
                "weknora_knowledge_base_id": "kb-default",
            },
        )
    )

    document_citation = _to_agent_citation(document_evidence)
    wiki_citation = _to_agent_citation(wiki_evidence)
    checker = CitationChecker()
    check = checker.validate(
        [document_citation, wiki_citation],
        evidence_items=[document_evidence, wiki_evidence],
    )
    if not check.valid:
        raise SmokeError("expected valid citations: " + "; ".join(check.warnings))

    fail_closed_checks = 0
    invalid_items = [
        Evidence(
            document_id=None,
            external_doc_id="wk-doc-001",
            chunk_id=None,
            title="Missing Chunk",
            text="cannot trace this document evidence",
            score=0.1,
            source="weknora_api",
            source_type="document_chunk",
            metadata={},
        ),
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            wiki_page_id=None,
            title="Missing Wiki",
            text="cannot trace this wiki evidence",
            score=0.1,
            source="weknora_api",
            source_type="wiki_page",
            metadata={},
        ),
    ]
    for item in invalid_items:
        try:
            builder.build(item)
        except CitationBindingError:
            fail_closed_checks += 1
        else:
            raise SmokeError("invalid evidence unexpectedly produced a citation")
    if builder.build_many(invalid_items):
        raise SmokeError("build_many must drop invalid evidence")

    bad_check = checker.validate([_to_agent_citation(document_evidence)], evidence_items=[])
    if bad_check.valid:
        raise SmokeError("citation without retrieved evidence unexpectedly passed")
    fail_closed_checks += 1

    saved_count = _assert_generation_service_persists(
        document_citation=document_citation,
        wiki_citation=wiki_citation,
    )
    return {
        "document_evidence_id": document_evidence.evidence_id,
        "wiki_evidence_id": wiki_evidence.evidence_id,
        "saved_citations": saved_count,
        "located_citations": saved_count,
        "fail_closed_checks": fail_closed_checks,
    }


def _to_agent_citation(evidence: Evidence) -> AgentCitation:
    return AgentCitation(
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        wiki_page_id=evidence.wiki_page_id,
        title=evidence.title,
        text=evidence.text,
        score=evidence.score,
        source=evidence.source,
        metadata=evidence.metadata,
    )


def _assert_generation_service_persists(
    document_citation: AgentCitation,
    wiki_citation: AgentCitation,
) -> int:
    with TemporaryDirectory(prefix="pa-weknora-citation-smoke-") as temp_dir:
        engine = create_engine(f"sqlite:///{Path(temp_dir) / 'smoke.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            _seed_locator_targets(session)
            task = create_task(session=session, task_type="knowledge_qa", title="fixture")
            _, citations = create_output_with_citations(
                session=session,
                task=task,
                title="fixture output",
                citations=[
                    _to_generation_citation(document_citation),
                    _to_generation_citation(wiki_citation),
                ],
                content_markdown="fixture output",
            )
            if len(citations) != 2:
                raise SmokeError(f"expected 2 saved citations, got {len(citations)}")
            located = 0
            for citation in citations:
                location = locate_citation(
                    session=session,
                    request=CitationLocateRequest(id=citation.id),
                )
                if not location.located:
                    raise SmokeError(f"citation was not locatable: {location.message}")
                if location.target_type not in {"document_chunk", "wiki_page"}:
                    raise SmokeError(f"unexpected locator target: {location.target_type}")
                located += 1
            if located != 2:
                raise SmokeError(f"expected 2 located citations, got {located}")
            return len(citations)


def _seed_locator_targets(session: Session) -> None:
    document = Document(
        id="doc-policy-001",
        title="Fixture Policy",
        knowledge_backend="weknora_api",
        external_doc_id="wk-doc-001",
        status="indexed",
    )
    chunk = DocumentChunk(
        id="chunk-policy-001",
        document_id=document.id,
        external_doc_id=document.external_doc_id,
        chunk_index=2,
        title="Fixture Policy",
        content="sanitized policy evidence",
        content_hash="fixture-policy-hash",
        token_count=3,
        char_count=25,
        source="weknora_api",
        embedding_status="indexed",
    )
    wiki_page = WikiPage(
        id="wiki-page-001",
        slug="fixture-wiki",
        title="Fixture Wiki",
        content_markdown="sanitized wiki evidence",
        status="published",
        embedding_status="indexed",
    )
    session.add(document)
    session.add(chunk)
    session.add(wiki_page)
    session.commit()


def _to_generation_citation(citation: AgentCitation) -> dict[str, Any]:
    return {
        "title": citation.title,
        "text": citation.text,
        "source": citation.source,
        "document_id": citation.document_id,
        "external_doc_id": citation.external_doc_id,
        "chunk_id": citation.chunk_id,
        "score": citation.score,
        "metadata_json": json.dumps(citation.metadata, ensure_ascii=False, sort_keys=True),
    }


if __name__ == "__main__":
    raise SystemExit(main())
