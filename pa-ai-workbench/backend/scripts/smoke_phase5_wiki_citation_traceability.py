"""Fixture smoke for P5-C3 Wiki citation traceability.

This checks that Wiki evidence can be bound, persisted, serialized, and
located back to the Wiki page. It uses sanitized fixture records only and does
not contact WeKnora.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app.models import WikiPage as WikiPageModel  # noqa: E402
from app.schemas import CitationLocateRequest  # noqa: E402
from app.schemas import CitationRead  # noqa: E402
from app.services.citation_locator_service import locate_citation  # noqa: E402
from app.services.generation_service import create_output_with_citations  # noqa: E402
from app.services.generation_service import create_task  # noqa: E402
from knowledge_engine.citations import CitationBuilder  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.wiki import WikiPageStatus  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the P5-C3 Wiki citation traceability contract fails."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 Wiki citation traceability smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Phase 5 Wiki citation traceability smoke passed (fixture)")
    print("- scope: fixture contract only; this is not real WeKnora PASS")
    print(f"- evidence id: {result['evidence_id']}")
    print(f"- wiki page id: {result['wiki_page_id']}")
    print(f"- local locate: {result['local_ui_hash']}")
    print(f"- remote locate: {result['remote_ui_hash']}")
    return 0


def _run_smoke() -> dict[str, str]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        page = _create_wiki_page(session)
        bound = CitationBuilder().build(_wiki_evidence(page))
        if bound.wiki_page_id != page.id:
            raise SmokeError(f"bound wiki_page_id mismatch: {bound.wiki_page_id}")
        if bound.evidence_id != f"wiki_page:{page.id}":
            raise SmokeError(f"bound evidence_id mismatch: {bound.evidence_id}")
        if bound.source_type != "wiki_page":
            raise SmokeError(f"bound source_type mismatch: {bound.source_type}")

        citation = _persist_wiki_citation(session=session, evidence=bound)
        read = CitationRead.model_validate(citation)
        _assert_read(read=read, page=page)

        local_target = locate_citation(
            session=session,
            request=CitationLocateRequest(
                id=citation.id,
                evidence_id=read.evidence_id,
                source_type=read.source_type,
                wiki_page_id=read.wiki_page_id,
                source=read.source,
                metadata_json=read.metadata_json,
            ),
        )
        if not local_target.located or local_target.target_type != "wiki_page":
            raise SmokeError(f"local locate failed: {local_target}")
        if local_target.ui_hash != "#/wiki?slug=phase5%2Fp5-c3-trace":
            raise SmokeError(f"local ui_hash mismatch: {local_target.ui_hash}")

        remote_target = locate_citation(
            session=session,
            request=CitationLocateRequest(
                source="weknora_api",
                metadata={
                    "citation_binding": {
                        "evidence_id": "wiki_page:remote-wiki-p5-c3",
                        "source_type": "wiki_page",
                        "wiki_page_id": "remote-wiki-p5-c3",
                        "metadata": {
                            "wiki_slug": "phase5/p5-c3-remote",
                            "weknora_wiki_page_id": "remote-wiki-p5-c3",
                        },
                    }
                },
            ),
        )
        if not remote_target.located or remote_target.ui_hash != "#/wiki?slug=phase5%2Fp5-c3-remote":
            raise SmokeError(f"remote locate failed: {remote_target}")

        return {
            "evidence_id": read.evidence_id or "",
            "wiki_page_id": read.wiki_page_id or "",
            "local_ui_hash": local_target.ui_hash or "",
            "remote_ui_hash": remote_target.ui_hash or "",
        }


def _create_wiki_page(session: Session) -> WikiPageModel:
    page = WikiPageModel(
        id="wiki-p5-c3",
        slug="phase5/p5-c3-trace",
        title="TEST-WIKI-001 P5-C3 Traceability Wiki",
        summary="P5-C3 synthetic Wiki traceability page.",
        content_markdown="TEST-WIKI-001 source_type=wiki_page citation locate fixture.",
        status=WikiPageStatus.PUBLISHED,
        page_type="wiki",
        metadata_json=json.dumps(
            {
                "anchor": "TEST-WIKI-001",
                "weknora_wiki_page_id": "wiki-p5-c3",
                "weknora_wiki_page_slug": "phase5/p5-c3-trace",
            },
            ensure_ascii=False,
        ),
    )
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


def _wiki_evidence(page: WikiPageModel) -> Evidence:
    return Evidence(
        document_id=None,
        external_doc_id=None,
        chunk_id=None,
        title=page.title,
        text=page.content_markdown,
        score=0.88,
        source="weknora_api",
        evidence_id=None,
        source_type="wiki_page",
        wiki_page_id=None,
        metadata={
            "id": page.id,
            "slug": page.slug,
            "weknora_wiki_page_id": page.id,
            "weknora_wiki_page_slug": page.slug,
            "anchor": "TEST-WIKI-001",
        },
    )


def _persist_wiki_citation(session: Session, evidence: Evidence):
    task = create_task(session=session, task_type="knowledge_qa", title="P5-C3 fixture")
    _, citations = create_output_with_citations(
        session=session,
        task=task,
        title="P5-C3 fixture output",
        citations=[
            {
                "title": evidence.title,
                "text": evidence.text,
                "source": evidence.source,
                "document_id": evidence.document_id,
                "external_doc_id": evidence.external_doc_id,
                "chunk_id": evidence.chunk_id,
                "score": evidence.score,
                "metadata_json": json.dumps(evidence.metadata, ensure_ascii=False, sort_keys=True),
            }
        ],
        content_markdown="P5-C3 fixture output",
    )
    if len(citations) != 1:
        raise SmokeError(f"expected one saved citation, got {len(citations)}")
    return citations[0]


def _assert_read(read: CitationRead, page: WikiPageModel) -> None:
    expected_evidence_id = f"wiki_page:{page.id}"
    expected = {
        "evidence_id": expected_evidence_id,
        "source_type": "wiki_page",
        "wiki_page_id": page.id,
    }
    actual = {
        "evidence_id": read.evidence_id,
        "source_type": read.source_type,
        "wiki_page_id": read.wiki_page_id,
    }
    for key, value in expected.items():
        if actual[key] != value:
            raise SmokeError(f"CitationRead {key} mismatch: {actual[key]} != {value}")
    metadata = _metadata(read)
    binding = metadata.get("citation_binding")
    if not isinstance(binding, dict):
        raise SmokeError("CitationRead metadata missing citation_binding")
    if binding.get("wiki_page_id") != page.id:
        raise SmokeError(f"binding wiki_page_id mismatch: {binding}")
    binding_metadata = binding.get("metadata")
    if not isinstance(binding_metadata, dict) or binding_metadata.get("wiki_slug") != page.slug:
        raise SmokeError(f"binding metadata wiki_slug missing: {binding_metadata}")


def _metadata(read: CitationRead) -> dict[str, Any]:
    try:
        parsed = json.loads(read.metadata_json or "{}")
    except json.JSONDecodeError as exc:
        raise SmokeError("CitationRead metadata_json is invalid") from exc
    if not isinstance(parsed, dict):
        raise SmokeError("CitationRead metadata_json must be an object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
