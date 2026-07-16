import json
from pathlib import Path
from typing import Any

from knowledge_engine.vectorstores.base import VectorStore
from knowledge_engine.vectorstores.schemas import VectorRecord
from knowledge_engine.vectorstores.schemas import VectorSearchRequest
from knowledge_engine.vectorstores.schemas import VectorSearchResult


class LocalChromaVectorStore(VectorStore):
    def __init__(
        self,
        path: str = "./data/chroma",
        collection_name: str = "pa_workbench_chunks",
        client: Any | None = None,
        collection: Any | None = None,
    ) -> None:
        self.path = str(path)
        self.collection_name = collection_name
        self.client = client or self._build_client(self.path)
        self.collection = collection or self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def health(self) -> dict:
        return {
            "status": "ok",
            "provider": "chroma",
            "path": self.path,
            "collection_name": self.collection_name,
            "record_count": self._count(),
        }

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self.collection.upsert(
            ids=[record.id for record in records],
            embeddings=[record.vector for record in records],
            documents=[record.text for record in records],
            metadatas=[
                self._sanitize_metadata(record.metadata) or None
                for record in records
            ],
        )

    def search(self, request: VectorSearchRequest) -> list[VectorSearchResult]:
        raw = self.collection.query(
            query_embeddings=[request.query_vector],
            n_results=request.top_k,
            where=self._sanitize_filters(request.filters) or None,
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        results = self._results_from_query(raw)
        if request.score_threshold is not None:
            results = [
                result for result in results if result.score >= request.score_threshold
            ]
        return results[: request.top_k]

    def delete(self, ids: list[str]) -> int:
        if not ids:
            return 0
        existing = self.collection.get(ids=ids, include=[])
        existing_ids = set(existing.get("ids") or [])
        if existing_ids:
            self.collection.delete(ids=list(existing_ids))
        return len(existing_ids)

    def clear(self) -> None:
        ids = self.collection.get(include=[]).get("ids") or []
        if ids:
            self.collection.delete(ids=ids)

    def _count(self) -> int:
        count = getattr(self.collection, "count", None)
        if callable(count):
            return int(count())
        return len(self.collection.get(include=[]).get("ids") or [])

    @staticmethod
    def _build_client(path: str) -> Any:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "chromadb is required for LocalChromaVectorStore. "
                "Install backend requirements."
            ) from exc

        Path(path).mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=path)

    @classmethod
    def _results_from_query(cls, raw: dict) -> list[VectorSearchResult]:
        ids = cls._first_batch(raw.get("ids"))
        documents = cls._first_batch(raw.get("documents"))
        metadatas = cls._first_batch(raw.get("metadatas"))
        distances = cls._first_batch(raw.get("distances"))
        embeddings = cls._first_batch(raw.get("embeddings"))

        results: list[VectorSearchResult] = []
        for index, record_id in enumerate(ids):
            distance = cls._value_at(distances, index, default=1.0)
            document = cls._value_at(documents, index, default="")
            metadata = cls._restore_metadata(
                cls._value_at(metadatas, index, default={}) or {}
            )
            embedding = cls._as_list(cls._value_at(embeddings, index, default=[]))
            results.append(
                VectorSearchResult(
                    record=VectorRecord(
                        id=str(record_id),
                        vector=[float(value) for value in embedding],
                        text=str(document or ""),
                        metadata=metadata,
                    ),
                    score=cls._score_from_distance(distance),
                )
            )
        return results

    @classmethod
    def _first_batch(cls, value: Any) -> list:
        normalized = cls._as_list(value)
        if not normalized:
            return []
        first = normalized[0]
        if isinstance(first, (list, tuple)) or hasattr(first, "tolist"):
            return cls._as_list(first)
        return normalized

    @staticmethod
    def _as_list(value: Any) -> list:
        if value is None:
            return []
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return list(value)

    @staticmethod
    def _value_at(values: list, index: int, default: Any) -> Any:
        return values[index] if index < len(values) else default

    @staticmethod
    def _score_from_distance(distance: Any) -> float:
        try:
            value = float(distance)
        except (TypeError, ValueError):
            return 0.0
        return 1.0 / (1.0 + max(value, 0.0))

    @classmethod
    def _sanitize_filters(cls, filters: dict[str, Any]) -> dict[str, Any]:
        return cls._sanitize_metadata(filters)

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return sanitized

    @staticmethod
    def _restore_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        restored: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, str) and value[:1] in {"[", "{"}:
                try:
                    restored[key] = json.loads(value)
                    continue
                except json.JSONDecodeError:
                    pass
            restored[key] = value
        return restored
