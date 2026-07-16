from abc import ABC
from abc import abstractmethod

from knowledge_engine.embeddings.schemas import EmbeddingVector


class EmbeddingProvider(ABC):
    """Unified boundary for all embedding model calls."""

    @abstractmethod
    def embed_text(self, text: str) -> EmbeddingVector:
        """Embed one text input."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        """Embed a batch of text inputs."""
