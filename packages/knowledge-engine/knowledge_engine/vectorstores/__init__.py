"""Vector store package for the extracted Knowledge Engine."""

from knowledge_engine.vectorstores.base import VectorStore
from knowledge_engine.vectorstores.factory import VectorStoreConfig
from knowledge_engine.vectorstores.factory import get_vector_store
from knowledge_engine.vectorstores.chroma_store import LocalChromaVectorStore
from knowledge_engine.vectorstores.mock_store import MockVectorStore
from knowledge_engine.vectorstores.schemas import VectorRecord
from knowledge_engine.vectorstores.schemas import VectorSearchRequest
from knowledge_engine.vectorstores.schemas import VectorSearchResult

__all__ = [
    "LocalChromaVectorStore",
    "MockVectorStore",
    "VectorRecord",
    "VectorSearchRequest",
    "VectorSearchResult",
    "VectorStoreConfig",
    "VectorStore",
    "get_vector_store",
]
