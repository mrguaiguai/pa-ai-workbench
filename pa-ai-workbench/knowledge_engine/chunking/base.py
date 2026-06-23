from abc import ABC
from abc import abstractmethod

from knowledge_engine.chunking.schemas import DocumentChunkCandidate
from knowledge_engine.parsers.schemas import ParsedDocument


class Chunker(ABC):
    @abstractmethod
    def chunk(self, document: ParsedDocument) -> list[DocumentChunkCandidate]:
        raise NotImplementedError
