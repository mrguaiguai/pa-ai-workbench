"""Smoke-check WeKnora Wiki publish/index status mapping for PA.

This fixture smoke validates P3-M1-C4 without a live WeKnora service:
- PA publish maps to WeKnora Wiki update with status=published.
- PA local Wiki metadata records publish sync and index-in-progress status.
- A post-publish retrieve can return traceable source_type=wiki_page evidence.
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
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def _set_smoke_env() -> None:
    os.environ["KNOWLEDGE_BACKEND"] = "weknora_api"
    os.environ["WEKNORA_BASE_URL"] = "http://weknora.fixture"
    os.environ["WEKNORA_SERVICE_TOKEN"] = "fixture-token"
    os.environ["WEKNORA_DEFAULT_KB_ID"] = "kb-fixture"


_set_smoke_env()

from app.config import get_settings  # noqa: E402
from app.models import WikiCitation  # noqa: E402
from app.models import WikiPage as WikiPageModel  # noqa: E402
from app.services import wiki_service  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402
from app.services.wiki_service import publish_wiki_page_record  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.wiki import WikiPageStatus  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the publish/index contract fails."""


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="http://weknora.fixture",
            service_token="fixture-token",
            default_kb_id="kb-fixture",
        )
        self.updated_payloads: list[dict[str, Any]] = []
        self.retrieve_payloads: list[dict[str, Any]] = []

    def update_wiki_page(
        self,
        slug: str,
        page: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        if kb_id != "kb-fixture":
            raise SmokeError(f"unexpected kb_id: {kb_id}")
        if slug != "publish-fixture":
            raise SmokeError(f"unexpected publish slug: {slug}")
        if page.get("status") != WikiPageStatus.PUBLISHED:
            raise SmokeError(f"publish did not send published status: {page}")
        self.updated_payloads.append(page)
        return WikiPage(
            slug=slug,
            title=str(page["title"]),
            page_type=str(page["page_type"]),
            summary=str(page.get("summary") or ""),
            content=str(page.get("content") or ""),
            citations=[],
            source="weknora_api",
            metadata={
                "id": "wiki-publish-fixture",
                "knowledge_base_id": "kb-fixture",
                "status": WikiPageStatus.PUBLISHED,
                "source_refs": page.get("source_refs") or [],
                "chunk_refs": page.get("chunk_refs") or [],
                "version": 7,
                "source": "weknora_api",
            },
        )

    def _request_json(  # type: ignore[override]
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if method != "POST" or path != "/api/v1/knowledge-search":
            raise SmokeError(f"unexpected retrieve request: {method} {path}")
        payload = payload or {}
        self.retrieve_payloads.append(payload)
        if payload.get("query") != "published policy":
            raise SmokeError(f"unexpected retrieve query: {payload}")
        return {
            "success": True,
            "data": [
                {
                    "id": "wiki-hit-001",
                    "source_type": "wiki_page",
                    "wiki_page_id": "wiki-publish-fixture",
                    "wiki_page_slug": "publish-fixture",
                    "wiki_title": "Publish Fixture",
                    "content": "Published wiki evidence excerpt.",
                    "score": 0.87,
                    "knowledge_base_id": "kb-fixture",
                    "match_type": "wiki",
                }
            ],
        }


def main() -> int:
    get_settings.cache_clear()
    fixture_backend = FixtureWeKnoraBackend()
    original_backend_factory = wiki_service._weknora_backend
    wiki_service._weknora_backend = lambda settings=None: fixture_backend  # type: ignore[assignment]
    try:
        result = _run_fixture_smoke(fixture_backend)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Wiki publish smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        wiki_service._weknora_backend = original_backend_factory  # type: ignore[assignment]
    print("WeKnora Wiki publish smoke passed (fixture)")
    print(f"- slug: {result['slug']}")
    print(f"- sync operation: {result['sync_operation']}")
    print(f"- index status: {result['index_status']}")
    print(f"- evidence id: {result['evidence_id']}")
    return 0


def _run_fixture_smoke(fixture_backend: FixtureWeKnoraBackend) -> dict[str, Any]:
    with TemporaryDirectory(prefix="pa-weknora-wiki-publish-smoke-"):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            page = WikiPageModel(
                slug="publish-fixture",
                title="Publish Fixture",
                summary="Publish fixture summary.",
                content_markdown="Published policy fixture body.",
                status=WikiPageStatus.DRAFT,
                page_type="policy_analysis",
                source_document_ids_json=json.dumps(["wk-doc-fixture"]),
                source_citation_ids_json=json.dumps(["cite_fixture"]),
                metadata_json=json.dumps(
                    {
                        "kb_id": "kb-fixture",
                        "weknora_id": "wiki-publish-fixture",
                        "weknora_sync_status": "synced",
                        "weknora_status": WikiPageStatus.DRAFT,
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
                    citation_id="cite_fixture",
                    evidence_id="document_chunk:wk-chunk-fixture",
                    source_type="document_chunk",
                    excerpt="Sanitized source excerpt.",
                    metadata_json=json.dumps({"citation_title": "Fixture Source"}),
                )
            )
            session.commit()

            published = publish_wiki_page_record(session=session, slug=page.slug)
            metadata = page_metadata(published)
            if published.status != WikiPageStatus.PUBLISHED:
                raise SmokeError("local page was not published")
            if published.embedding_status != "indexing":
                raise SmokeError(f"unexpected local index status: {published.embedding_status}")
            if metadata.get("weknora_sync_operation") != "publish":
                raise SmokeError(f"publish sync metadata missing: {metadata}")
            if metadata.get("weknora_status") != WikiPageStatus.PUBLISHED:
                raise SmokeError("WeKnora published status was not stored")
            if metadata.get("weknora_index_status") != "indexing":
                raise SmokeError("WeKnora index status was not stored")

            evidence_items = fixture_backend.retrieve(
                query="published policy",
                filters={"source_type": "wiki_page"},
                top_k=3,
            )
            if len(evidence_items) != 1:
                raise SmokeError(f"expected one wiki evidence, got {len(evidence_items)}")
            evidence = evidence_items[0]
            if evidence.source_type != "wiki_page":
                raise SmokeError(f"unexpected evidence source_type: {evidence.source_type}")
            if evidence.wiki_page_id != "wiki-publish-fixture":
                raise SmokeError(f"unexpected wiki_page_id: {evidence.wiki_page_id}")
            if evidence.evidence_id != "wiki_page:wiki-publish-fixture":
                raise SmokeError(f"unexpected evidence_id: {evidence.evidence_id}")
            if not fixture_backend.updated_payloads:
                raise SmokeError("publish did not call WeKnora update")
            return {
                "slug": published.slug,
                "sync_operation": metadata.get("weknora_sync_operation"),
                "index_status": metadata.get("weknora_index_status"),
                "evidence_id": evidence.evidence_id,
            }


if __name__ == "__main__":
    raise SystemExit(main())
