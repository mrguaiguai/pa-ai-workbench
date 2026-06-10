"""Fixture smoke for P3-M2-A3 Wiki async status recovery.

Uses an in-memory DB and fake WeKnora backend. It does not read .env, call live
WeKnora, or print Wiki body content.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import os
from pathlib import Path
import sys
from typing import Iterator

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.config import Settings  # noqa: E402
from app.models import utc_now  # noqa: E402
from app.schemas import WikiPageCreateRequest  # noqa: E402
from app.services import wiki_service  # noqa: E402
from app.services.wiki_service import create_wiki_page_record  # noqa: E402
from app.services.wiki_service import get_wiki_page_record  # noqa: E402
from app.services.wiki_service import publish_wiki_page_record  # noqa: E402
from app.services.wiki_service import recover_wiki_page_status  # noqa: E402
from app.services.wiki_service import refresh_wiki_page_status  # noqa: E402
from app.services.wiki_service import wiki_status_summary  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the fixture contract fails."""


class FixtureWeKnoraBackend:
    def __init__(self) -> None:
        self.fail_create = False
        self.fail_update = False
        self.readable = True
        self.retrievable_slugs: set[str] = set()
        self.create_calls = 0
        self.update_calls = 0

    def create_wiki_page(self, page: dict, kb_id: str | None = None) -> WikiPage:
        self.create_calls += 1
        if self.fail_create:
            raise KnowledgeBackendUnavailableError("fixture create failure")
        return self._page(page, kb_id)

    def update_wiki_page(
        self,
        slug: str,
        page: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        self.update_calls += 1
        if self.fail_update:
            raise KnowledgeBackendUnavailableError("fixture publish failure")
        return self._page({**page, "slug": slug}, kb_id)

    def read_wiki_page(self, slug: str, kb_id: str | None = None) -> WikiPage | None:
        if not self.readable:
            return None
        return WikiPage(
            slug=slug,
            title=f"Fixture {slug}",
            page_type="fixture",
            summary="Fixture summary.",
            content="Fixture content.",
            citations=[],
            source="weknora_api",
            metadata={"id": f"wk-{slug}", "knowledge_base_id": kb_id, "status": "published"},
        )

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        return [
            Evidence(
                evidence_id=f"wiki_page:wk-{slug}",
                source_type="wiki_page",
                document_id=None,
                external_doc_id=None,
                chunk_id=None,
                wiki_page_id=f"wk-{slug}",
                title=f"Fixture {slug}",
                text="Fixture excerpt.",
                score=None,
                source="weknora_api",
                metadata={
                    "weknora_wiki_page_slug": slug,
                    "weknora_knowledge_base_id": (filters or {}).get("knowledge_base_ids", ["kb-fixture"])[0],
                },
            )
            for slug in sorted(self.retrievable_slugs)
        ][:top_k]

    def _page(self, page: dict, kb_id: str | None) -> WikiPage:
        slug = str(page.get("slug") or "")
        return WikiPage(
            slug=slug,
            title=str(page.get("title") or "Fixture"),
            page_type=str(page.get("page_type") or "fixture"),
            summary=str(page.get("summary") or ""),
            content=str(page.get("content") or ""),
            citations=[],
            source="weknora_api",
            metadata={
                "id": f"wk-{slug}",
                "knowledge_base_id": kb_id or "kb-fixture",
                "status": page.get("status") or "draft",
            },
        )


@contextmanager
def patched_runtime(backend: FixtureWeKnoraBackend) -> Iterator[None]:
    original_settings = wiki_service.get_settings
    original_backend = wiki_service._weknora_backend
    settings = Settings(
        knowledge_backend="weknora_api",
        weknora_base_url="http://weknora.fixture",
        weknora_service_token="fixture-token",
        weknora_default_kb_id="kb-fixture",
    )
    wiki_service.get_settings = lambda: settings  # type: ignore[assignment]
    wiki_service._weknora_backend = lambda settings=None: backend  # type: ignore[assignment]
    original_timeout = os.environ.get("WIKI_INDEX_TIMEOUT_SECONDS")
    os.environ["WIKI_INDEX_TIMEOUT_SECONDS"] = "1"
    try:
        yield
    finally:
        wiki_service.get_settings = original_settings  # type: ignore[assignment]
        wiki_service._weknora_backend = original_backend  # type: ignore[assignment]
        if original_timeout is None:
            os.environ.pop("WIKI_INDEX_TIMEOUT_SECONDS", None)
        else:
            os.environ["WIKI_INDEX_TIMEOUT_SECONDS"] = original_timeout


def main() -> int:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    backend = FixtureWeKnoraBackend()
    with patched_runtime(backend), Session(engine) as session:
        draft = create_wiki_page_record(session, _payload("draft-state"))
        _assert(wiki_status_summary(draft)["wiki_state"] == "draft", "draft state mismatch")

        backend.fail_create = True
        sync_failed = create_wiki_page_record(session, _payload("sync-failed"))
        summary = wiki_status_summary(sync_failed)
        _assert(summary["wiki_state"] == "sync_failed", "sync failed not identified")
        _assert(summary["wiki_retryable"] is True, "sync failed not retryable")
        backend.fail_create = False

        publish_failed = create_wiki_page_record(session, _payload("publish-failed"))
        backend.fail_update = True
        publish_wiki_page_record(session, "publish-failed")
        publish_failed = get_wiki_page_record(session, "publish-failed")
        _assert(publish_failed is not None, "publish failed page missing")
        summary = wiki_status_summary(publish_failed)
        _assert(summary["wiki_state"] == "publish_failed", "publish failed not identified")
        backend.fail_update = False

        not_retrievable = create_wiki_page_record(session, _payload("not-retrievable"))
        publish_wiki_page_record(session, "not-retrievable")
        backend.readable = False
        refreshed = refresh_wiki_page_status(session, "not-retrievable")
        summary = wiki_status_summary(refreshed)
        _assert(
            summary["wiki_state"] == "published_not_retrievable",
            "published-not-retrievable not identified",
        )
        backend.readable = True

        timed_out = create_wiki_page_record(session, _payload("index-timeout"))
        publish_wiki_page_record(session, "index-timeout")
        timed_out = get_wiki_page_record(session, "index-timeout")
        _assert(timed_out is not None, "timeout page missing")
        timed_out.published_at = utc_now() - timedelta(seconds=5)
        timed_out.updated_at = timed_out.published_at
        session.add(timed_out)
        session.commit()
        refreshed = refresh_wiki_page_status(session, "index-timeout")
        summary = wiki_status_summary(refreshed)
        _assert(summary["wiki_state"] == "index_timeout", "index timeout not identified")
        _assert(summary["wiki_retryable"] is True, "index timeout not retryable")

        retrievable = create_wiki_page_record(session, _payload("retrievable"))
        publish_wiki_page_record(session, "retrievable")
        backend.retrievable_slugs.add("retrievable")
        refreshed = refresh_wiki_page_status(session, "retrievable")
        summary = wiki_status_summary(refreshed)
        _assert(summary["wiki_state"] == "retrievable", "retrievable not identified")
        _assert(summary["wiki_retrievable"] is True, "retrievable flag false")

        recovered, message = recover_wiki_page_status(session, "index-timeout")
        _assert("recovery submitted" in message, "recover message mismatch")
        _assert(recovered.status == "published", "recover changed publish status")

    print(
        "Wiki status recovery M2 smoke passed "
        "(fixture: sync failed, publish failed, not retrievable, timeout, retrievable)"
    )
    return 0


def _payload(slug: str) -> WikiPageCreateRequest:
    return WikiPageCreateRequest(
        slug=slug,
        title=f"Fixture {slug}",
        summary="Synthetic Wiki status fixture.",
        content_markdown="Synthetic Wiki status fixture body.",
        page_type="fixture",
        metadata={"source": "fixture"},
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
