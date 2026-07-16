import os

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.backends import ExtractedKnowledgeBackend
from knowledge_engine.backends import MockKnowledgeBackend
from knowledge_engine.backends import WeKnoraApiBackend
from knowledge_engine.capabilities import normalize_backend_name
from knowledge_engine.capabilities import should_fail_closed_for_unavailable_backend
from knowledge_engine.errors import KnowledgeBackendUnavailableError

SUPPORTED_BACKENDS = {"mock", "weknora_api", "extracted"}


def create_knowledge_engine(backend_name: str | None = None) -> KnowledgeEngine:
    selected = normalize_backend_name(backend_name or os.getenv("KNOWLEDGE_BACKEND", "mock"))
    if selected == "mock":
        return MockKnowledgeBackend()
    if selected == "weknora_api":
        backend = WeKnoraApiBackend()
        if backend.configured:
            return backend
        if should_fail_closed_for_unavailable_backend(selected):
            raise KnowledgeBackendUnavailableError(
                "WeKnora backend is selected but required config is incomplete."
            )
        return MockKnowledgeBackend()
    if selected == "extracted":
        return ExtractedKnowledgeBackend()

    # Keep MVP demoable for unknown or not-yet-implemented backends.
    if should_fail_closed_for_unavailable_backend(selected):
        raise KnowledgeBackendUnavailableError(f"Unsupported knowledge backend: {selected}")
    return MockKnowledgeBackend()
