from dataclasses import dataclass
from dataclasses import field
import os

from knowledge_engine.vectorstores.base import VectorStore


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


@dataclass(frozen=True)
class VectorStoreConfig:
    provider: str = field(default_factory=lambda: _get_str("VECTOR_STORE_PROVIDER", "mock"))
    path: str = field(default_factory=lambda: _get_str("VECTOR_STORE_PATH", "./data/chroma"))
    collection_name: str = field(
        default_factory=lambda: _get_str(
            "VECTOR_COLLECTION_NAME",
            "pa_workbench_chunks",
        )
    )


def get_vector_store(config: VectorStoreConfig | None = None) -> VectorStore:
    resolved = config or VectorStoreConfig()
    provider = resolved.provider.strip().lower()
    if provider == "mock":
        from knowledge_engine.vectorstores.mock_store import MockVectorStore

        return MockVectorStore(name=resolved.collection_name)
    if provider in {"chroma", "local_chroma", "local-chroma"}:
        from knowledge_engine.vectorstores.chroma_store import LocalChromaVectorStore

        return LocalChromaVectorStore(
            path=resolved.path,
            collection_name=resolved.collection_name,
        )
    raise NotImplementedError(
        f"Vector store provider is not implemented yet: {resolved.provider}. "
        "Supported providers: mock, chroma."
    )
