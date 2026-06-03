from abc import ABC
from abc import abstractmethod

from knowledge_engine.vectorstores.schemas import VectorRecord
from knowledge_engine.vectorstores.schemas import VectorSearchRequest
from knowledge_engine.vectorstores.schemas import VectorSearchResult


class VectorStore(ABC):
    @abstractmethod
    def health(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, request: VectorSearchRequest) -> list[VectorSearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
