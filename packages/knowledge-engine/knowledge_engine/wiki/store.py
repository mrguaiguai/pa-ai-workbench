from abc import ABC
from abc import abstractmethod

from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary


class WikiStore(ABC):
    @abstractmethod
    def search(
        self,
        query: str = "",
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        raise NotImplementedError

    @abstractmethod
    def read(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        raise NotImplementedError


class InMemoryWikiStore(WikiStore):
    def __init__(self, pages: list[WikiPage] | None = None) -> None:
        self._pages = {page.slug: page for page in pages or []}

    def search(
        self,
        query: str = "",
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        normalized_query = query.strip().lower()
        pages = [
            page
            for page in self._pages.values()
            if self._matches_kb(page.metadata, kb_id)
            and self._matches_query(page, normalized_query)
        ]
        return [
            WikiPageSummary(
                slug=page.slug,
                title=page.title,
                page_type=page.page_type,
                summary=page.summary,
                source=page.source,
                metadata=page.metadata,
            )
            for page in pages[:limit]
        ]

    def read(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        page = self._pages.get(slug)
        if page is None or not self._matches_kb(page.metadata, kb_id):
            return None
        return page

    def upsert(self, page: WikiPage) -> None:
        self._pages[page.slug] = page

    @staticmethod
    def _matches_kb(metadata: dict, kb_id: str | None) -> bool:
        return kb_id is None or metadata.get("kb_id") == kb_id

    @staticmethod
    def _matches_query(page: WikiPage, normalized_query: str) -> bool:
        if not normalized_query:
            return True
        return (
            normalized_query in page.slug.lower()
            or normalized_query in page.title.lower()
            or normalized_query in page.summary.lower()
            or normalized_query in page.content.lower()
        )
