import hashlib
import math

from knowledge_engine.embeddings.base import EmbeddingProvider
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig
from knowledge_engine.embeddings.schemas import EmbeddingVector
from knowledge_engine.embeddings.schemas import hash_embedding_text


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: EmbeddingProviderConfig | None = None) -> None:
        self.config = config or EmbeddingProviderConfig()
        if self.config.dimension <= 0:
            raise ValueError("EMBEDDING_DIMENSION must be positive")

    def embed_text(self, text: str) -> EmbeddingVector:
        if not isinstance(text, str):
            raise TypeError("Embedding text must be a string")

        vector = self._vector_for_text(text)
        return EmbeddingVector(
            text_hash=hash_embedding_text(text),
            vector=vector,
            dimension=self.config.dimension,
            provider="mock",
            model=self.config.model_name,
            metadata={
                "mock": True,
                "text_chars": len(text),
            },
        )

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed_text(text) for text in texts]

    def _vector_for_text(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self.config.dimension:
            digest = hashlib.sha256(f"{text}\n{counter}".encode("utf-8")).digest()
            for offset in range(0, len(digest), 4):
                if len(values) >= self.config.dimension:
                    break
                raw = int.from_bytes(digest[offset : offset + 4], "big")
                values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
            counter += 1
        return self._normalize(values)

    @staticmethod
    def _normalize(values: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return values
        return [value / norm for value in values]
