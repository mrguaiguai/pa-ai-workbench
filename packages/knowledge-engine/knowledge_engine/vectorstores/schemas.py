from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("VectorRecord.id must not be empty")
        if not self.vector:
            raise ValueError("VectorRecord.vector must not be empty")
        object.__setattr__(self, "vector", [float(value) for value in self.vector])

    @property
    def dimension(self) -> int:
        return len(self.vector)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class VectorSearchRequest:
    query_vector: list[float]
    top_k: int = 8
    filters: dict[str, Any] = field(default_factory=dict)
    score_threshold: float | None = None

    def __post_init__(self) -> None:
        if not self.query_vector:
            raise ValueError("VectorSearchRequest.query_vector must not be empty")
        if self.top_k <= 0:
            raise ValueError("VectorSearchRequest.top_k must be positive")
        object.__setattr__(
            self,
            "query_vector",
            [float(value) for value in self.query_vector],
        )

    @property
    def dimension(self) -> int:
        return len(self.query_vector)


@dataclass(frozen=True)
class VectorSearchResult:
    record: VectorRecord
    score: float

    def to_dict(self) -> dict:
        return {
            "record": self.record.to_dict(),
            "score": self.score,
        }
