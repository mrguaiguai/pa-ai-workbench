from abc import ABC
from abc import abstractmethod

from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary


class KnowledgeEngine(ABC):
    @abstractmethod
    def health(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        raise NotImplementedError

    @abstractmethod
    def get_document_status(self, external_doc_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        raise NotImplementedError

    @abstractmethod
    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        raise NotImplementedError

    @abstractmethod
    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        raise NotImplementedError

