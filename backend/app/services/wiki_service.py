from app import pathing as _pathing  # noqa: F401

from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary


def search_wiki_pages(
    query: str,
    kb_id: str | None = None,
    limit: int = 10,
) -> list[WikiPageSummary]:
    engine = create_knowledge_engine()
    return engine.search_wiki(query=query, kb_id=kb_id, limit=limit)


def read_wiki_page(slug: str, kb_id: str | None = None) -> WikiPage | None:
    engine = create_knowledge_engine()
    return engine.read_wiki_page(slug=slug, kb_id=kb_id)
