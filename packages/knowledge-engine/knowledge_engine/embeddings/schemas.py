from dataclasses import dataclass
from dataclasses import field
import hashlib
from typing import Any


def hash_embedding_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Embedding text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmbeddingVector:
    text_hash: str
    vector: list[float]
    dimension: int
    provider: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text_hash:
            raise ValueError("EmbeddingVector.text_hash must not be empty")
        if not self.provider:
            raise ValueError("EmbeddingVector.provider must not be empty")
        if not self.model:
            raise ValueError("EmbeddingVector.model must not be empty")
        if self.dimension <= 0:
            raise ValueError("EmbeddingVector.dimension must be positive")
        if len(self.vector) != self.dimension:
            raise ValueError("EmbeddingVector.dimension must match vector length")
        object.__setattr__(self, "vector", [float(value) for value in self.vector])
