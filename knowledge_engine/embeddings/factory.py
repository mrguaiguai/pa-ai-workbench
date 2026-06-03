from dataclasses import dataclass
from dataclasses import field
import os

from knowledge_engine.embeddings.base import EmbeddingProvider


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


@dataclass(frozen=True)
class EmbeddingProviderConfig:
    provider: str = field(default_factory=lambda: _get_str("EMBEDDING_PROVIDER", "mock"))
    base_url: str = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", ""))
    api_key: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY", ""),
        repr=False,
    )
    model_name: str = field(
        default_factory=lambda: _get_str("EMBEDDING_MODEL_NAME", "mock-embedding")
    )
    dimension: int = field(default_factory=lambda: _get_int("EMBEDDING_DIMENSION", 1024))
    timeout_seconds: int = field(
        default_factory=lambda: _get_int("EMBEDDING_TIMEOUT_SECONDS", 60)
    )


def get_embedding_provider(
    config: EmbeddingProviderConfig | None = None,
) -> EmbeddingProvider:
    resolved = config or EmbeddingProviderConfig()
    provider = resolved.provider.strip().lower()
    if provider in {"mock", "mock_embedding"}:
        from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider

        return MockEmbeddingProvider(resolved)

    raise NotImplementedError(
        f"Embedding provider is not implemented yet: {resolved.provider}. "
        "G8 adds the OpenAI-compatible provider."
    )
