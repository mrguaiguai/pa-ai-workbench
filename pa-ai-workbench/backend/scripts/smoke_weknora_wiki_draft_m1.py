"""Smoke-check WeKnora Wiki draft/create/update sync for PA.

This fixture smoke validates P3-M1-C3 without a live WeKnora service:
- PA keeps the local output -> draft workflow.
- WeKnora create receives a draft page with PA provenance in page_metadata.
- WeKnora create/update payloads preserve source_refs and chunk_refs.
- PA local Wiki metadata records WeKnora sync status and external page id.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
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


def _set_smoke_env() -> None:
    os.environ["KNOWLEDGE_BACKEND"] = "weknora_api"
    os.environ["WEKNORA_BASE_URL"] = "http://weknora.fixture"
    os.environ["WEKNORA_SERVICE_TOKEN"] = "fixture-token"
    os.environ["WEKNORA_DEFAULT_KB_ID"] = "kb-fixture"
    os.environ["CHAT_MODEL_PROVIDER"] = "mock"
    os.environ["CHAT_MODEL_NAME"] = "mock-chat"
    os.environ["CHAT_MODEL_API_KEY"] = ""
    os.environ["MOCK_MODEL_MODE"] = "true"


_set_smoke_env()

from app.config import get_settings  # noqa: E402
from app.models import Citation  # noqa: E402
from app.models import GeneratedOutput  # noqa: E402
from app.schemas import WikiDraftFromOutputRequest  # noqa: E402
from app.schemas import WikiPageUpdateRequest  # noqa: E402
from app.services import wiki_service  # noqa: E402
from app.services.wiki_service import create_wiki_draft_from_output  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402
from app.services.wiki_service import read_wiki_page  # noqa: E402
from app.services.wiki_service import update_wiki_page_record  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.wiki import WikiPageStatus  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the Wiki draft sync contract fails."""


class FixtureWeKnoraBackend:
    def __init__(self) -> None:
        self.created_payloads: list[dict[str, Any]] = []
        self.updated_payloads: list[dict[str, Any]] = []
        self.synced_slug: str | None = None

    def create_wiki_page(self, page: dict, kb_id: str | None = None) -> WikiPage:
        if kb_id != "kb-fixture":
            raise SmokeError(f"unexpected create kb_id: {kb_id}")
        self.created_payloads.append(page)
        _assert_weknora_payload(page=page, expected_status=WikiPageStatus.DRAFT)
        self.synced_slug = str(page.get("slug") or "")
        return _synced_page(page=page, version=1)

    def update_wiki_page(
        self,
        slug: str,
        page: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        if kb_id != "kb-fixture":
            raise SmokeError(f"unexpected update kb_id: {kb_id}")
        if slug != self.synced_slug:
            raise SmokeError(f"unexpected update slug: {slug}")
        self.updated_payloads.append(page)
        _assert_weknora_payload(page=page, expected_status=WikiPageStatus.DRAFT)
        if "updated fixture paragraph" not in page.get("content", ""):
            raise SmokeError("updated content was not sent to WeKnora")
        return _synced_page(page=page, version=2)


def main() -> int:
    get_settings.cache_clear()
    fixture_backend = FixtureWeKnoraBackend()
    original_backend_factory = wiki_service._weknora_backend
    wiki_service._weknora_backend = lambda settings=None: fixture_backend  # type: ignore[assignment]
    try:
        result = _run_fixture_smoke(fixture_backend)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Wiki draft smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        wiki_service._weknora_backend = original_backend_factory  # type: ignore[assignment]
    print("WeKnora Wiki draft smoke passed (fixture)")
    print(f"- slug: {result['slug']}")
    print(f"- sync status: {result['sync_status']}")
    print(f"- create calls: {result['create_calls']}")
    print(f"- update calls: {result['update_calls']}")
    return 0


def _run_fixture_smoke(fixture_backend: FixtureWeKnoraBackend) -> dict[str, Any]:
    with TemporaryDirectory(prefix="pa-weknora-wiki-draft-smoke-"):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            output = GeneratedOutput(
                task_id="task_fixture",
                task_type="policy_analysis",
                title="C3 Fixture Output",
                content_markdown=(
                    "## Fixture Policy Draft\n\n"
                    "Keep a sanitized evidence note and an owner in every update."
                ),
                status="completed",
            )
            session.add(output)
            session.commit()
            session.refresh(output)

            citation = Citation(
                task_id=output.task_id,
                output_id=output.id,
                document_id="doc-fixture",
                external_doc_id="wk-doc-fixture",
                chunk_id="wk-chunk-fixture",
                title="Fixture Source",
                text="Sanitized citation excerpt for the fixture.",
                score=0.91,
                source="weknora_api",
                metadata_json=json.dumps(
                    {
                        "evidence_id": "document_chunk:wk-chunk-fixture",
                        "citation_source_type": "document_chunk",
                    },
                    ensure_ascii=False,
                ),
            )
            session.add(citation)
            session.commit()

            draft = create_wiki_draft_from_output(
                session=session,
                output_id=output.id,
                payload=WikiDraftFromOutputRequest(
                    slug="c3-fixture-draft",
                    title="C3 Fixture Draft",
                    summary="Fixture Wiki draft summary.",
                    tags=["c3", "fixture"],
                    business_area="public_affairs",
                    page_type="policy_analysis",
                    created_by="c3_smoke",
                    metadata={"kb_id": "kb-fixture"},
                ),
            )
            metadata = page_metadata(draft)
            if metadata.get("weknora_sync_status") != "synced":
                raise SmokeError(f"unexpected sync status: {metadata}")
            expected_weknora_id = f"wiki-{draft.slug}"
            if metadata.get("weknora_id") != expected_weknora_id:
                raise SmokeError("WeKnora external id was not stored")
            if metadata.get("weknora_source_refs") != ["wk-doc-fixture|Fixture Source"]:
                raise SmokeError("WeKnora source refs were not stored")
            if metadata.get("weknora_chunk_refs") != ["wk-chunk-fixture"]:
                raise SmokeError("WeKnora chunk refs were not stored")
            local_page = read_wiki_page(slug=draft.slug, session=session)
            if local_page is None or local_page.slug != draft.slug:
                raise SmokeError("local draft could not be read after sync")

            updated = update_wiki_page_record(
                session=session,
                slug=draft.slug,
                payload=WikiPageUpdateRequest(
                    content_markdown=(
                        draft.content_markdown
                        + "\n\nAdditional updated fixture paragraph."
                    )
                ),
            )
            updated_metadata = page_metadata(updated)
            if updated_metadata.get("weknora_sync_operation") != "update":
                raise SmokeError(
                    f"update sync operation was not recorded: {updated_metadata}"
                )
            if updated_metadata.get("weknora_version") != 2:
                raise SmokeError("WeKnora update version was not recorded")
            return {
                "slug": updated.slug,
                "sync_status": updated_metadata.get("weknora_sync_status"),
                "create_calls": len(fixture_backend.created_payloads),
                "update_calls": len(fixture_backend.updated_payloads),
            }


def _assert_weknora_payload(page: dict[str, Any], expected_status: str) -> None:
    if not str(page.get("slug") or "").startswith("c3-fixture-draft"):
        raise SmokeError(f"unexpected payload slug: {page.get('slug')}")
    if page.get("status") != expected_status:
        raise SmokeError(f"unexpected payload status: {page.get('status')}")
    if page.get("source_refs") != ["wk-doc-fixture|Fixture Source"]:
        raise SmokeError(f"source_refs were not preserved: {page.get('source_refs')}")
    if page.get("chunk_refs") != ["wk-chunk-fixture"]:
        raise SmokeError(f"chunk_refs were not preserved: {page.get('chunk_refs')}")
    page_metadata = page.get("page_metadata")
    if not isinstance(page_metadata, dict):
        raise SmokeError("page_metadata was not sent")
    if page_metadata.get("pa_source_output_id") is None:
        raise SmokeError("PA source output id was not sent")
    if page_metadata.get("pa_source_citation_ids") == []:
        raise SmokeError("PA source citation ids were not sent")


def _synced_page(page: dict[str, Any], version: int) -> WikiPage:
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
            "knowledge_base_id": "kb-fixture",
            "status": page.get("status"),
            "source_refs": page.get("source_refs") or [],
            "chunk_refs": page.get("chunk_refs") or [],
            "version": version,
            "source": "weknora_api",
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
