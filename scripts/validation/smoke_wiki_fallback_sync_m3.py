"""Fixture smoke for P3-M3-B3 Wiki fallback sync state.

Uses sanitized in-memory fixtures only. It validates that explicit extracted
Wiki fallback can create/read/search/update/publish locally, while status fields
make it clear that WeKnora sync is pending and the page is not retrievable by
WeKnora.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Iterator

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
from app.api.wiki import _wiki_page_to_read  # noqa: E402
from app.config import Settings  # noqa: E402
from app.schemas import WikiPageCreateRequest  # noqa: E402
from app.services import wiki_service  # noqa: E402
from app.services.wiki_service import create_wiki_page_record  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402
from app.services.wiki_service import publish_wiki_page_record  # noqa: E402
from app.services.wiki_service import wiki_status_summary  # noqa: E402
from knowledge_engine.backends import ExtractedKnowledgeBackend  # noqa: E402


DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_WIKI_FALLBACK_SYNC.md"


class SmokeError(RuntimeError):
    """Raised when Wiki fallback sync expectations fail."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Wiki fallback sync smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Wiki fallback sync smoke passed")
    print(f"- adapter wiki state: {result['adapter_wiki_state']}")
    print(f"- adapter retrievable: {result['adapter_retrievable']}")
    print(f"- db wiki state: {result['db_wiki_state']}")
    print(f"- db retrievable: {result['db_retrievable']}")
    print(f"- conflict status: {result['sync_conflict_status']}")
    return 0


def _run_smoke() -> dict[str, object]:
    _assert_doc()
    adapter_result = _assert_extracted_adapter_wiki()
    db_result = _assert_pa_db_wiki_fallback()
    return {
        **adapter_result,
        **db_result,
    }


def _assert_extracted_adapter_wiki() -> dict[str, object]:
    backend = ExtractedKnowledgeBackend()
    created = backend.create_wiki_page(
        {
            "slug": "fallback-sync-fixture",
            "title": "Fallback Sync Fixture",
            "page_type": "policy",
            "summary": "Sanitized local fallback summary.",
            "content": "Sanitized local fallback content.",
            "metadata": {"kb_id": "kb-local-fixture"},
            "citations": [
                {
                    "document_id": "pa-doc-local-fixture",
                    "chunk_id": "local-chunk-1",
                    "source_type": "document_chunk",
                    "excerpt": "Sanitized citation excerpt.",
                    "title": "Fallback source",
                }
            ],
        }
    )
    _assert(created.source == "extracted", "created adapter page source mismatch")
    _assert(created.metadata.get("wiki_state") == "draft", "created page not draft")
    _assert(created.metadata.get("weknora_retrievable") is False, "draft claimed retrievable")

    searched = backend.search_wiki("fallback", kb_id="kb-local-fixture", limit=5)
    _assert(searched, "adapter search missed local page")
    _assert(searched[0].source == "extracted", "adapter search source mismatch")

    updated = backend.update_wiki_page(
        "fallback-sync-fixture",
        {"summary": "Updated sanitized local fallback summary."},
        kb_id="kb-local-fixture",
    )
    _assert(updated.summary.startswith("Updated"), "adapter update did not apply")

    published = backend.publish_wiki_page("fallback-sync-fixture")
    _assert(published.metadata.get("wiki_state") == "sync_pending", "published page not sync pending")
    _assert(published.metadata.get("weknora_sync_status") == "pending", "sync status not pending")
    _assert(published.metadata.get("weknora_retrievable") is False, "published page claimed retrievable")

    indexed = backend.index_wiki_page("fallback-sync-fixture")
    _assert(indexed.get("status") == "sync_pending", "adapter index status mismatch")
    _assert(indexed.get("wiki_retrievable") is False, "adapter index claimed retrievable")

    read_model = _wiki_page_to_read(published)
    _assert(read_model.source == "extracted", "API read model source mismatch")
    _assert(read_model.wiki_state == "sync_pending", "API read model state mismatch")
    _assert(read_model.wiki_retrievable is False, "API read model claimed retrievable")

    return {
        "adapter_wiki_state": published.metadata.get("wiki_state"),
        "adapter_retrievable": published.metadata.get("weknora_retrievable"),
        "sync_conflict_status": published.metadata.get("sync_conflict_status"),
    }


def _assert_pa_db_wiki_fallback() -> dict[str, object]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with patched_extracted_settings(), Session(engine) as session:
        draft = create_wiki_page_record(
            session=session,
            payload=WikiPageCreateRequest(
                slug="db-fallback-sync",
                title="DB Fallback Sync",
                summary="Sanitized DB fallback summary.",
                content_markdown="Sanitized DB fallback body.",
                page_type="policy",
                metadata={"kb_id": "kb-local-fixture"},
            ),
        )
        draft_summary = wiki_status_summary(draft)
        _assert(draft_summary["wiki_state"] == "draft", "DB draft state mismatch")
        draft_metadata = page_metadata(draft)
        _assert(draft_metadata.get("fallback_backend") == "extracted", "DB draft missing fallback backend")
        _assert(draft_metadata.get("weknora_retrievable") is False, "DB draft claimed retrievable")

        published = publish_wiki_page_record(session=session, slug="db-fallback-sync")
        published_summary = wiki_status_summary(published)
        published_metadata = page_metadata(published)
        _assert(published_summary["wiki_state"] == "sync_pending", "DB published state mismatch")
        _assert(published_summary["wiki_retrievable"] is False, "DB summary claimed retrievable")
        _assert(published_metadata.get("weknora_sync_status") == "pending", "DB sync not pending")
        _assert(published_metadata.get("weknora_index_status") == "not_synced", "DB index status mismatch")

    return {
        "db_wiki_state": published_summary["wiki_state"],
        "db_retrievable": published_summary["wiki_retrievable"],
    }


@contextmanager
def patched_extracted_settings() -> Iterator[None]:
    original_settings = wiki_service.get_settings
    settings = Settings(
        knowledge_backend="extracted",
        mock_mode=False,
    )
    wiki_service.get_settings = lambda: settings  # type: ignore[assignment]
    try:
        yield
    finally:
        wiki_service.get_settings = original_settings  # type: ignore[assignment]


def _assert_doc() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for phrase in (
        "p3-m3-b3",
        "source=extracted",
        "sync_pending",
        "wiki_retrievable=false",
        "sync_conflict_status",
    ):
        _assert(phrase in text, f"fallback doc missing phrase: {phrase}")


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
