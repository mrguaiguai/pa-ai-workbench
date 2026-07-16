"""Smoke-check Wiki citation/source ref mapping for PA API responses.

This fixture smoke validates P3-M1-C5 without a live WeKnora service:
- Local PA Wiki records expose source output, document refs, and citation ids.
- WeKnora Wiki metadata refs are normalized into PA WikiPageRead fields.
- Remote source_refs/chunk_refs produce display-only wiki_citations for Bindings.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app.api.wiki import _page_record_to_read  # noqa: E402
from app.api.wiki import _wiki_page_to_read  # noqa: E402
from app.models import WikiCitation  # noqa: E402
from app.models import WikiPage as WikiPageModel  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.wiki import WikiPageStatus  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the Wiki ref mapping contract fails."""


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Wiki refs smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora Wiki refs smoke passed (fixture)")
    print(f"- local output id: {result['local_output_id']}")
    print(f"- remote document id: {result['remote_document_id']}")
    print(f"- remote citation id: {result['remote_citation_id']}")
    print(f"- remote chunk id: {result['remote_chunk_id']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    with TemporaryDirectory(prefix="pa-weknora-wiki-refs-smoke-"):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            local = _local_response(session)
            remote = _remote_response()
    return {
        "local_output_id": local.source_output_id,
        "remote_document_id": remote.source_document_ids[0],
        "remote_citation_id": remote.source_citation_ids[0],
        "remote_chunk_id": remote.wiki_citations[0].chunk_id,
    }


def _local_response(session: Session):
    page = WikiPageModel(
        slug="refs-fixture",
        title="Refs Fixture",
        summary="Refs fixture summary.",
        content_markdown="Refs fixture body.",
        status=WikiPageStatus.DRAFT,
        page_type="policy_analysis",
        source_output_id="out-fixture",
        source_document_ids_json=json.dumps(["doc-fixture"]),
        source_citation_ids_json=json.dumps(["cite-fixture"]),
        metadata_json=json.dumps(
            {
                "kb_id": "kb-fixture",
                "weknora_source_refs": ["wk-doc-fixture|Fixture Source"],
                "weknora_chunk_refs": ["wk-chunk-fixture"],
            },
            ensure_ascii=False,
        ),
    )
    session.add(page)
    session.commit()
    session.refresh(page)
    session.add(
        WikiCitation(
            wiki_page_id=page.id,
            external_doc_id="wk-doc-fixture",
            chunk_id="wk-chunk-fixture",
            output_id="out-fixture",
            citation_id="cite-fixture",
            evidence_id="document_chunk:wk-chunk-fixture",
            source_type="document_chunk",
            excerpt="Sanitized source excerpt.",
            score=0.91,
            metadata_json=json.dumps({"citation_title": "Fixture Source"}),
        )
    )
    session.commit()

    response = _page_record_to_read(session=session, page=page)
    if response.source_output_id != "out-fixture":
        raise SmokeError(f"local source_output_id missing: {response}")
    if response.source_document_ids != ["doc-fixture"]:
        raise SmokeError(f"local source_document_ids missing: {response.source_document_ids}")
    if response.source_citation_ids != ["cite-fixture"]:
        raise SmokeError(f"local source_citation_ids missing: {response.source_citation_ids}")
    if len(response.wiki_citations) != 1:
        raise SmokeError(f"local wiki_citations missing: {response.wiki_citations}")
    local_citation = response.wiki_citations[0]
    if local_citation.output_id != "out-fixture":
        raise SmokeError(f"local output binding missing: {local_citation}")
    if local_citation.citation_id != "cite-fixture":
        raise SmokeError(f"local citation binding missing: {local_citation}")
    if response.metadata.get("wiki_citations") is None:
        raise SmokeError("local metadata did not include wiki_citations")
    return response


def _remote_response():
    page = WikiPage(
        slug="remote-refs-fixture",
        title="Remote Refs Fixture",
        page_type="policy_analysis",
        summary="Remote refs fixture summary.",
        content="Remote refs fixture body.",
        citations=[],
        source="weknora_api",
        metadata={
            "id": "wiki-remote-fixture",
            "status": WikiPageStatus.PUBLISHED,
            "pa_source_output_id": "out-remote-fixture",
            "pa_source_document_ids": ["pa-doc-fixture"],
            "pa_source_citation_ids": ["cite-remote-fixture"],
            "source_refs": ["wk-doc-fixture|Fixture Source"],
            "chunk_refs": ["wk-chunk-fixture"],
            "created_at": "2026-06-09T00:00:00+00:00",
        },
    )
    response = _wiki_page_to_read(page)
    if response.source_output_id != "out-remote-fixture":
        raise SmokeError(f"remote source_output_id missing: {response.source_output_id}")
    if response.source_document_ids != ["pa-doc-fixture", "wk-doc-fixture"]:
        raise SmokeError(f"remote source docs not normalized: {response.source_document_ids}")
    if response.source_citation_ids != ["cite-remote-fixture"]:
        raise SmokeError(f"remote source citations missing: {response.source_citation_ids}")
    if len(response.wiki_citations) != 1:
        raise SmokeError(f"remote wiki_citations missing: {response.wiki_citations}")
    citation = response.wiki_citations[0]
    if citation.external_doc_id != "wk-doc-fixture":
        raise SmokeError(f"remote external_doc_id missing: {citation.external_doc_id}")
    if citation.chunk_id != "wk-chunk-fixture":
        raise SmokeError(f"remote chunk_id missing: {citation.chunk_id}")
    if citation.output_id != "out-remote-fixture":
        raise SmokeError(f"remote output binding missing: {citation.output_id}")
    if citation.citation_id != "cite-remote-fixture":
        raise SmokeError(f"remote citation binding missing: {citation.citation_id}")
    if citation.evidence_id != "document_chunk:wk-chunk-fixture":
        raise SmokeError(f"remote evidence_id missing: {citation.evidence_id}")
    if citation.metadata.get("reference_only") is not True:
        raise SmokeError(f"remote reference flag missing: {citation.metadata}")
    return response


if __name__ == "__main__":
    raise SystemExit(main())
