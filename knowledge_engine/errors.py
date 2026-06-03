class KnowledgeEngineError(Exception):
    """Base error for Knowledge Engine failures."""


class KnowledgeBackendUnavailableError(KnowledgeEngineError):
    """Raised when a configured knowledge backend cannot be reached."""


class KnowledgeDocumentNotFoundError(KnowledgeEngineError):
    """Raised when a document lookup cannot be resolved by the backend."""

