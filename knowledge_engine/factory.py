import os

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.backends import ExtractedKnowledgeBackend
from knowledge_engine.backends import MockKnowledgeBackend
from knowledge_engine.backends import WeKnoraApiBackend

SUPPORTED_BACKENDS = {"mock", "weknora_api", "extracted"}


def create_knowledge_engine(backend_name: str | None = None) -> KnowledgeEngine:
    selected = (backend_name or os.getenv("KNOWLEDGE_BACKEND", "mock")).strip().lower()
    if selected == "mock":
        return MockKnowledgeBackend()
    if selected == "weknora_api":
        backend = WeKnoraApiBackend()
        if backend.configured:
            return backend
        return MockKnowledgeBackend()
    if selected == "extracted":
        return ExtractedKnowledgeBackend()

    # Keep MVP demoable for unknown or not-yet-implemented backends.
    return MockKnowledgeBackend()
