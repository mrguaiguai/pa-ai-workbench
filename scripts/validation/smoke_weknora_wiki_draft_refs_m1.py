"""Smoke-check Wiki draft refs from Agent output citations.

This fixture smoke covers P3-M1-D5:
- output -> draft keeps PA output/citation ids in draft metadata;
- WeKnora source_refs/chunk_refs/evidence refs are available before publish;
- WikiDraftWriterTool preserves normalized ref metadata;
- the WeKnora draft payload receives the same traceable refs.

The script uses sanitized fixture records and an in-memory database. It does
not require live WeKnora, secrets, uploads, backend/data, or real documents.
"""

from __future__ import annotations

import json
from pathlib import Path
import os
import sys
from typing import Any

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


def _set_smoke_env() -> None:
    os.environ["KNOWLEDGE_BACKEND"] = "weknora_api"
    os.environ["WEKNORA_BASE_URL"] = "fixture://weknora"
    os.environ["WEKNORA_SERVICE_TOKEN"] = "fixture-token"
    os.environ["WEKNORA_DEFAULT_KB_ID"] = "kb-d5-fixture"
    os.environ["MOCK_MODE"] = "false"
    os.environ["CHAT_MODEL_PROVIDER"] = "mock"
    os.environ["CHAT_MODEL_NAME"] = "mock-chat"
    os.environ["CHAT_MODEL_API_KEY"] = ""
    os.environ["MOCK_MODEL_MODE"] = "true"


_set_smoke_env()

from agent.tools.wiki_draft_writer import WikiDraftWriterTool  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models import Citation  # noqa: E402
from app.models import GeneratedOutput  # noqa: E402
from app.schemas import WikiDraftFromOutputRequest  # noqa: E402
from app.services import wiki_service  # noqa: E402
from app.services.wiki_service import create_wiki_draft_from_output  # noqa: E402
from app.services.wiki_service import list_wiki_citation_records  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the Wiki draft refs contract fails."""


class FixtureWeKnoraBackend:
    def __init__(self) -> None:
        self.created_payloads: list[dict[str, Any]] = []

    def create_wiki_page(self, page: dict, kb_id: str | None = None) -> WikiPage:
        if kb_id != "kb-d5-fixture":
            raise SmokeError(f"unexpected create kb_id: {kb_id}")
        self.created_payloads.append(page)
        _assert_weknora_payload(page)
        slug = str(page["slug"])
        return WikiPage(
            slug=slug,
            title=str(page["title"]),
            page_type=str(page["page_type"]),
            summary=str(page.get("summary") or ""),
            content=str(page.get("content") or ""),
            citations=[],
            source="weknora_api",
            metadata={
                "id": f"wiki-{slug}",
                "knowledge_base_id": "kb-d5-fixture",
                "status": page.get("status"),
                "source_refs": page.get("source_refs") or [],
                "chunk_refs": page.get("chunk_refs") or [],
                "source": "weknora_api",
            },
        )


def main() -> int:
    get_settings.cache_clear()
    fixture_backend = FixtureWeKnoraBackend()
    original_backend_factory = wiki_service._weknora_backend
    wiki_service._weknora_backend = lambda settings=None: fixture_backend  # type: ignore[assignment]
    try:
        result = _run_fixture_smoke(fixture_backend)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Wiki draft refs smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        wiki_service._weknora_backend = original_backend_factory  # type: ignore[assignment]
    print("WeKnora Wiki draft refs smoke passed (fixture)")
    print(f"- slug: {result['slug']}")
    print(f"- source refs: {', '.join(result['source_refs'])}")
    print(f"- chunk refs: {', '.join(result['chunk_refs'])}")
    print(f"- evidence refs: {result['evidence_ref_count']}")
    print(f"- tool refs preserved: {result['tool_refs_preserved']}")
    return 0


def _run_fixture_smoke(fixture_backend: FixtureWeKnoraBackend) -> dict[str, Any]:
    _assert_wiki_draft_writer_tool_refs()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        output = GeneratedOutput(
            task_id="task_d5_fixture",
            task_type="knowledge_qa",
            title="D5 Fixture Output",
            content_markdown=(
                "## D5 Fixture Output\n\n"
                "This sanitized output should become a traceable Wiki draft."
            ),
            status="completed",
        )
        session.add(output)
        session.commit()
        session.refresh(output)

        document_citation = Citation(
            task_id=output.task_id,
            output_id=output.id,
            external_doc_id="wk-doc-d5",
            chunk_id="wk-chunk-d5",
            title="D5 Fixture Document",
            text="Sanitized document evidence for D5.",
            score=0.87,
            source="weknora_api",
            metadata_json=json.dumps(
                {
                    "evidence_id": "document_chunk:wk-chunk-d5",
                    "citation_source_type": "document_chunk",
                },
                ensure_ascii=False,
            ),
        )
        wiki_citation = Citation(
            task_id=output.task_id,
            output_id=output.id,
            title="D5 Fixture Wiki Source",
            text="Sanitized wiki-page evidence for D5.",
            score=0.74,
            source="weknora_api",
            metadata_json=json.dumps(
                {
                    "evidence_id": "wiki_page:wiki-source-d5",
                    "citation_source_type": "wiki_page",
                    "wiki_page_id": "wiki-source-d5",
                },
                ensure_ascii=False,
            ),
        )
        session.add(document_citation)
        session.add(wiki_citation)
        session.commit()
        session.refresh(document_citation)
        session.refresh(wiki_citation)

        draft = create_wiki_draft_from_output(
            session=session,
            output_id=output.id,
            payload=WikiDraftFromOutputRequest(
                slug="d5-fixture-draft",
                title="D5 Fixture Draft",
                summary="Fixture draft refs summary.",
                tags=["d5", "fixture"],
                business_area="public_affairs",
                page_type="knowledge_qa",
                created_by="d5_smoke",
                metadata={"kb_id": "kb-d5-fixture"},
            ),
        )

        metadata = page_metadata(draft)
        expected_citation_ids = [document_citation.id, wiki_citation.id]
        if metadata.get("pa_source_output_id") != output.id:
            raise SmokeError(f"source output metadata missing: {metadata}")
        if metadata.get("pa_source_citation_ids") != expected_citation_ids:
            raise SmokeError(f"source citation metadata missing: {metadata}")
        if metadata.get("weknora_source_refs") != ["wk-doc-d5|D5 Fixture Document"]:
            raise SmokeError(f"source refs metadata missing: {metadata}")
        if metadata.get("weknora_chunk_refs") != ["wk-chunk-d5"]:
            raise SmokeError(f"chunk refs metadata missing: {metadata}")
        evidence_refs = metadata.get("weknora_evidence_refs")
        if not isinstance(evidence_refs, list) or len(evidence_refs) != 2:
            raise SmokeError(f"evidence refs metadata missing: {metadata}")
        evidence_ids = {ref.get("evidence_id") for ref in evidence_refs}
        if evidence_ids != {"document_chunk:wk-chunk-d5", "wiki_page:wiki-source-d5"}:
            raise SmokeError(f"unexpected evidence refs: {evidence_refs}")

        citations = list_wiki_citation_records(session=session, wiki_page_id=draft.id)
        if len(citations) != 2:
            raise SmokeError(f"expected 2 wiki citations, got {len(citations)}")
        source_types = {citation.source_type for citation in citations}
        if source_types != {"document_chunk", "wiki_page"}:
            raise SmokeError(f"unexpected wiki citation source types: {source_types}")
        if len(fixture_backend.created_payloads) != 1:
            raise SmokeError("WeKnora draft create was not called exactly once")

        return {
            "slug": draft.slug,
            "source_refs": metadata["weknora_source_refs"],
            "chunk_refs": metadata["weknora_chunk_refs"],
            "evidence_ref_count": len(evidence_refs),
            "tool_refs_preserved": True,
        }


def _assert_wiki_draft_writer_tool_refs() -> None:
    tool = WikiDraftWriterTool()
    result = tool.write_from_output(
        output_id="out-d5-tool",
        title="D5 Tool Draft",
        metadata={
            "pa_source_citation_ids": ["cite-d5-tool"],
            "weknora_source_refs": ["wk-doc-tool|Tool Source"],
            "weknora_chunk_refs": ["wk-chunk-tool"],
            "weknora_evidence_refs": [
                {
                    "evidence_id": "document_chunk:wk-chunk-tool",
                    "source_type": "document_chunk",
                    "chunk_id": "wk-chunk-tool",
                }
            ],
        },
    )
    metadata = result.metadata
    if metadata.get("pa_source_output_id") != "out-d5-tool":
        raise SmokeError(f"tool source output metadata missing: {metadata}")
    if metadata.get("pa_source_citation_ids") != ["cite-d5-tool"]:
        raise SmokeError(f"tool citation refs not preserved: {metadata}")
    if metadata.get("weknora_chunk_refs") != ["wk-chunk-tool"]:
        raise SmokeError(f"tool chunk refs not preserved: {metadata}")
    evidence_refs = metadata.get("weknora_evidence_refs")
    if not isinstance(evidence_refs, list) or len(evidence_refs) != 1:
        raise SmokeError(f"tool evidence refs not preserved: {metadata}")


def _assert_weknora_payload(page: dict[str, Any]) -> None:
    if page.get("source_refs") != ["wk-doc-d5|D5 Fixture Document"]:
        raise SmokeError(f"source_refs were not sent to WeKnora: {page}")
    if page.get("chunk_refs") != ["wk-chunk-d5"]:
        raise SmokeError(f"chunk_refs were not sent to WeKnora: {page}")
    metadata = page.get("page_metadata")
    if not isinstance(metadata, dict):
        raise SmokeError("page_metadata was not sent to WeKnora")
    if metadata.get("pa_source_output_id") is None:
        raise SmokeError(f"PA output id was not sent: {metadata}")
    if len(metadata.get("weknora_evidence_refs") or []) != 2:
        raise SmokeError(f"evidence refs were not sent: {metadata}")


if __name__ == "__main__":
    raise SystemExit(main())
