import os

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.backends import MockKnowledgeBackend

SUPPORTED_BACKENDS = {"mock"}


def create_knowledge_engine(backend_name: str | None = None) -> KnowledgeEngine:
    selected = (backend_name or os.getenv("KNOWLEDGE_BACKEND", "mock")).strip().lower()
    if selected == "mock":
        return MockKnowledgeBackend()

    # C4/C5 will add concrete non-mock backends. Until then, keep MVP demoable.
    return MockKnowledgeBackend()

