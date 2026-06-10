class KnowledgeEngineError(Exception):
    """Base error for Knowledge Engine failures."""


class KnowledgeBackendUnavailableError(KnowledgeEngineError):
    """Raised when a configured knowledge backend cannot be reached."""


class KnowledgeDocumentNotFoundError(KnowledgeEngineError):
    """Raised when a document lookup cannot be resolved by the backend."""


class WeKnoraUnavailableError(KnowledgeBackendUnavailableError):
    """Base typed error for WeKnora adapter failures."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "weknora_unavailable",
        status_code: int | None = None,
        operation: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.operation = operation
        self.retryable = retryable

    def __str__(self) -> str:
        status = f" HTTP {self.status_code}" if self.status_code is not None else ""
        operation = f" during {self.operation}" if self.operation else ""
        return f"WeKnora{status} error{operation} ({self.error_code}): {self.message}"

    def to_public_dict(self) -> dict[str, object]:
        """Return a stable, sanitized shape suitable for API/log boundaries."""
        return {
            "status_code": self.status_code,
            "error_code": self.error_code,
            "message": self.message,
            "operation": self.operation,
            "retryable": self.retryable,
        }


class WeKnoraAuthError(WeKnoraUnavailableError):
    """Raised for WeKnora authentication or authorization failures."""


class WeKnoraTimeoutError(WeKnoraUnavailableError):
    """Raised when WeKnora does not respond before the configured timeout."""


class WeKnoraRateLimitError(WeKnoraUnavailableError):
    """Raised when WeKnora asks callers to slow down."""


class WeKnoraNotFoundError(WeKnoraUnavailableError):
    """Raised when WeKnora returns a not-found response."""


class WeKnoraServerError(WeKnoraUnavailableError):
    """Raised when WeKnora returns a retryable server-side error."""


class WeKnoraNetworkError(WeKnoraUnavailableError):
    """Raised when PA cannot establish a network connection to WeKnora."""


class WeKnoraDocumentError(WeKnoraUnavailableError):
    """Raised for document-scoped WeKnora failures."""


class WeKnoraWikiError(WeKnoraUnavailableError):
    """Raised for wiki-scoped WeKnora failures."""


class WeKnoraResponseMappingError(WeKnoraUnavailableError):
    """Raised when a WeKnora response cannot be safely parsed or mapped."""
