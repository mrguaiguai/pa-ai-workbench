from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class RetrieveRequest:
    query: str
    filters: dict[str, Any] = field(default_factory=dict)
    top_k: int = 8
    score_threshold: float | None = None

    @property
    def normalized_query(self) -> str:
        return self.query.strip()
