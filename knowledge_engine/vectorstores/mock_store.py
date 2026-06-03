import math
from threading import RLock
from typing import Any

from knowledge_engine.vectorstores.base import VectorStore
from knowledge_engine.vectorstores.schemas import VectorRecord
from knowledge_engine.vectorstores.schemas import VectorSearchRequest
from knowledge_engine.vectorstores.schemas import VectorSearchResult


class MockVectorStore(VectorStore):
    def __init__(self, name: str = "mock") -> None:
        self.name = name
        self._records: dict[str, VectorRecord] = {}
        self._dimension: int | None = None
        self._lock = RLock()

    def health(self) -> dict:
        with self._lock:
            return {
                "status": "ok",
                "provider": "mock",
                "name": self.name,
                "record_count": len(self._records),
                "dimension": self._dimension,
            }

    def upsert(self, records: list[VectorRecord]) -> None:
        with self._lock:
            for record in records:
                self._validate_record_dimension(record)
            for record in records:
                self._records[record.id] = record

    def search(self, request: VectorSearchRequest) -> list[VectorSearchResult]:
        with self._lock:
            self._validate_query_dimension(request)
            results = [
                VectorSearchResult(
                    record=record,
                    score=self._cosine_similarity(request.query_vector, record.vector),
                )
                for record in self._records.values()
                if self._matches_filters(record.metadata, request.filters)
            ]

        if request.score_threshold is not None:
            results = [
                result for result in results if result.score >= request.score_threshold
            ]
        results.sort(key=lambda result: result.score, reverse=True)
        return results[: request.top_k]

    def delete(self, ids: list[str]) -> int:
        deleted = 0
        with self._lock:
            for record_id in ids:
                if record_id in self._records:
                    del self._records[record_id]
                    deleted += 1
            if not self._records:
                self._dimension = None
        return deleted

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._dimension = None

    def _validate_record_dimension(self, record: VectorRecord) -> None:
        if self._dimension is None:
            self._dimension = record.dimension
            return
        if record.dimension != self._dimension:
            raise ValueError(
                "VectorRecord dimension does not match existing vector store dimension"
            )

    def _validate_query_dimension(self, request: VectorSearchRequest) -> None:
        if self._dimension is None:
            return
        if request.dimension != self._dimension:
            raise ValueError(
                "VectorSearchRequest dimension does not match vector store dimension"
            )

    @staticmethod
    def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        if not filters:
            return True
        return all(metadata.get(key) == value for key, value in filters.items())

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        dot = sum(
            left_value * right_value
            for left_value, right_value in zip(left, right, strict=True)
        )
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)
