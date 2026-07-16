"""Smoke-check M1 Wiki draft/publish/index status contract.

This fixture smoke covers P3-M1-E4:
- WikiPageRead exposes draft pages as not searchable;
- published pages are distinguishable before indexing;
- indexed pages expose embedding/vector/indexed_at fields for RAG availability.
"""

from __future__ import annotations

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
from app.api.wiki import create_wiki  # noqa: E402
from app.api.wiki import publish_wiki  # noqa: E402
from app.api.wiki import reindex_wiki  # noqa: E402
from app.schemas import WikiPageCreateRequest  # noqa: E402
from knowledge_engine.embeddings.schemas import EmbeddingVector  # noqa: E402
from knowledge_engine.embeddings.schemas import hash_embedding_text  # noqa: E402
from knowledge_engine.vectorstores.schemas import VectorSearchResult  # noqa: E402
import app.services.wiki_service as wiki_service  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the Wiki status contract fails."""


class FixtureEmbeddingProvider:
    def embed_text(self, text: str) -> EmbeddingVector:
        return EmbeddingVector(
            text_hash=hash_embedding_text(text),
            vector=[0.1, 0.2, 0.3],
            dimension=3,
            provider="fixture",
            model="fixture-embedding",
        )


class FixtureVectorStore:
    def __init__(self) -> None:
        self.records = {}

    def health(self) -> dict:
        return {"status": "ok", "source": "fixture"}

    def upsert(self, records) -> None:
        for record in records:
            self.records[record.id] = record

    def search(self, request) -> list[VectorSearchResult]:
        del request
        return []

    def delete(self, ids: list[str]) -> int:
        deleted = 0
        for record_id in ids:
            if record_id in self.records:
                deleted += 1
                del self.records[record_id]
        return deleted

    def clear(self) -> None:
        self.records.clear()


def main() -> int:
    original_embedding_provider = wiki_service.get_embedding_provider
    original_vector_store = wiki_service.get_vector_store
    wiki_service.get_embedding_provider = lambda: FixtureEmbeddingProvider()  # type: ignore[assignment]
    wiki_service.get_vector_store = lambda: FixtureVectorStore()  # type: ignore[assignment]
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora wiki status E4 smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        wiki_service.get_embedding_provider = original_embedding_provider  # type: ignore[assignment]
        wiki_service.get_vector_store = original_vector_store  # type: ignore[assignment]

    print("WeKnora wiki status E4 smoke passed (fixture)")
    print(f"- draft searchable: {result['draft_searchable']}")
    print(f"- published searchable: {result['published_searchable']}")
    print(f"- indexed searchable: {result['indexed_searchable']}")
    print(f"- indexed vector: {result['indexed_vector']}")
    return 0


def _run_fixture_smoke() -> dict[str, object]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        draft = create_wiki(
            payload=WikiPageCreateRequest(
                slug="e4-status-fixture",
                title="E4 Status Fixture",
                summary="Fixture page for Wiki status display.",
                content_markdown="Draft content that should not be searchable yet.",
                tags=["fixture"],
                metadata={"source": "fixture"},
            ),
            session=session,
        )
        if draft.status != "draft":
            raise SmokeError(f"draft status mismatch: {draft.status}")
        if _is_searchable(draft):
            raise SmokeError("draft page was marked searchable")

        published = publish_wiki(slug=draft.slug, session=session)
        if published.status != "published" or not published.published_at:
            raise SmokeError("published page did not expose published status/time")
        if _is_searchable(published):
            raise SmokeError("published-but-not-indexed page was marked searchable")

        indexed = reindex_wiki(slug=draft.slug, session=session)
        if indexed.status != "published":
            raise SmokeError(f"indexed page lost published status: {indexed.status}")
        if indexed.embedding_status != "indexed":
            raise SmokeError(f"indexed page missing embedding status: {indexed.embedding_status}")
        if not indexed.vector_id or not indexed.indexed_at:
            raise SmokeError("indexed page missing vector_id or indexed_at")
        if not _is_searchable(indexed):
            raise SmokeError("indexed page was not marked searchable")

    return {
        "draft_searchable": _is_searchable(draft),
        "published_searchable": _is_searchable(published),
        "indexed_searchable": _is_searchable(indexed),
        "indexed_vector": indexed.vector_id,
    }


def _is_searchable(page) -> bool:
    return (
        page.status == "published"
        and (
            page.embedding_status == "indexed"
            or bool(page.vector_id)
            or bool(page.indexed_at)
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
