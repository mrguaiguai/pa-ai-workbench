from abc import ABC
from abc import abstractmethod

from knowledge_engine.parsers.schemas import ParsedDocument


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, metadata: dict | None = None) -> ParsedDocument:
        raise NotImplementedError
