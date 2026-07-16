"""Smoke-check M1 history output to Wiki draft refs.

This fixture smoke covers P3-M1-E5:
- history/generated output can be converted into a Wiki draft;
- WeKnora citation refs survive in draft metadata and wiki_citations;
- mock citations remain as citations but are not promoted to WeKnora refs.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app import models as _models  # noqa: E402,F401
from app.schemas import WikiDraftFromOutputRequest  # noqa: E402
from app.services.generation_service import create_output_with_citations  # noqa: E402
from app.services.generation_service import create_task  # noqa: E402
from app.services.wiki_service import create_wiki_draft_from_output  # noqa: E402
from app.services.wiki_service import list_wiki_citation_records  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when history to Wiki draft refs are not preserved."""


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora history draft E5 smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora history draft E5 smoke passed (fixture)")
    print(f"- real draft citations: {result['real_draft_citations']}")
    print(f"- real evidence refs: {result['real_evidence_refs']}")
    print(f"- mock draft citations: {result['mock_draft_citations']}")
    print(f"- mock weknora refs: {result['mock_weknora_refs']}")
    return 0


def _run_fixture_smoke() -> dict[str, int]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        real_output = _create_output(
            session=session,
            title="E5 Real WeKnora Output",
            source="weknora_api",
            document_id="doc-e5-real",
            external_doc_id="wk-doc-e5",
            chunk_id="wk-chunk-e5",
            evidence_id="document_chunk:wk-chunk-e5",
            metadata={
                "source": "weknora_api",
                "evidence_id": "document_chunk:wk-chunk-e5",
                "citation_source_type": "document_chunk",
            },
        )
        real_draft = create_wiki_draft_from_output(
            session=session,
            output_id=real_output.id,
            payload=WikiDraftFromOutputRequest(metadata={"source": "history_page"}),
        )
        real_metadata = page_metadata(real_draft)
        real_citations = list_wiki_citation_records(session=session, wiki_page_id=real_draft.id)
        if len(real_citations) != 1:
            raise SmokeError("real draft did not preserve wiki citation binding")
        if real_citations[0].evidence_id != "document_chunk:wk-chunk-e5":
            raise SmokeError(f"real evidence id lost: {real_citations[0].evidence_id}")
        if real_metadata.get("weknora_chunk_refs") != ["wk-chunk-e5"]:
            raise SmokeError(f"real chunk refs lost: {real_metadata.get('weknora_chunk_refs')}")
        if real_metadata.get("weknora_evidence_refs") != [
            {
                "evidence_id": "document_chunk:wk-chunk-e5",
                "source_type": "document_chunk",
                "chunk_id": "wk-chunk-e5",
                "external_doc_id": "wk-doc-e5",
                "document_id": "doc-e5-real",
            }
        ]:
            raise SmokeError(f"real evidence refs lost: {real_metadata.get('weknora_evidence_refs')}")

        mock_output = _create_output(
            session=session,
            title="E5 Mock Output",
            source="mock",
            document_id="mock-doc-e5",
            external_doc_id=None,
            chunk_id="mock-chunk-e5",
            evidence_id=None,
            metadata={"source": "mock"},
        )
        mock_draft = create_wiki_draft_from_output(
            session=session,
            output_id=mock_output.id,
            payload=WikiDraftFromOutputRequest(metadata={"source": "history_page"}),
        )
        mock_metadata = page_metadata(mock_draft)
        mock_citations = list_wiki_citation_records(session=session, wiki_page_id=mock_draft.id)
        if len(mock_citations) != 1:
            raise SmokeError("mock draft did not preserve citation binding")
        if mock_citations[0].metadata_json and "mock" not in mock_citations[0].metadata_json:
            raise SmokeError("mock citation source marker was lost")
        for key in ("weknora_source_refs", "weknora_chunk_refs", "weknora_evidence_refs"):
            if mock_metadata.get(key):
                raise SmokeError(f"mock output was promoted to {key}: {mock_metadata.get(key)}")

    return {
        "real_draft_citations": len(real_citations),
        "real_evidence_refs": len(real_metadata.get("weknora_evidence_refs") or []),
        "mock_draft_citations": len(mock_citations),
        "mock_weknora_refs": sum(
            len(mock_metadata.get(key) or [])
            for key in ("weknora_source_refs", "weknora_chunk_refs", "weknora_evidence_refs")
        ),
    }


def _create_output(
    session: Session,
    title: str,
    source: str,
    document_id: str | None,
    external_doc_id: str | None,
    chunk_id: str | None,
    evidence_id: str | None,
    metadata: dict,
):
    task = create_task(
        session=session,
        task_type="knowledge_qa",
        title=title,
        status="completed",
        current_step="completed",
        progress=100,
    )
    output, _ = create_output_with_citations(
        session=session,
        task=task,
        title=title,
        content_json=json.dumps({"answer": title}, ensure_ascii=False),
        content_markdown=f"# {title}\n\nFixture answer.",
        warnings_json="[]",
        status="completed",
        citations=[
            {
                "document_id": document_id,
                "external_doc_id": external_doc_id,
                "chunk_id": chunk_id,
                "title": f"{title} citation",
                "text": f"{title} citation excerpt.",
                "score": 0.88 if source != "mock" else None,
                "source": source,
                "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            }
        ],
    )
    return output


if __name__ == "__main__":
    raise SystemExit(main())
