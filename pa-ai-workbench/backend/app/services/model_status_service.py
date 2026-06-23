from app.config import Settings
from app.schemas import ModelProviderStatus
from app.schemas import ModelStatusResponse

MOCK_CHAT_PROVIDERS = {"mock", "mock_chat"}
MOCK_EMBEDDING_PROVIDERS = {"mock", "mock_embedding"}
OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai-compatible", "openai_compatible"}


def get_model_status(settings: Settings) -> ModelStatusResponse:
    chat = _chat_status(settings)
    embedding = _embedding_status(settings)
    return ModelStatusResponse(
        chat_provider=chat.provider,
        embedding_provider=embedding.provider,
        mock_mode=settings.mock_model_mode,
        configured=chat.configured and embedding.configured,
        chat=chat,
        embedding=embedding,
    )


def _chat_status(settings: Settings) -> ModelProviderStatus:
    provider = _normalize_provider(settings.chat_model_provider)
    is_mock = provider in MOCK_CHAT_PROVIDERS
    is_openai_compatible = provider in OPENAI_COMPATIBLE_PROVIDERS
    configured = is_mock or (
        is_openai_compatible
        and bool(settings.chat_model_base_url.strip())
        and bool(settings.chat_model_name.strip())
    )
    return ModelProviderStatus(
        provider=provider,
        model=settings.chat_model_name,
        configured=configured,
        mock=is_mock,
        base_url_configured=bool(settings.chat_model_base_url.strip()),
        api_key_configured=bool(settings.chat_model_api_key.strip()),
        timeout_seconds=settings.chat_model_timeout_seconds,
        temperature=settings.chat_model_temperature,
    )


def _embedding_status(settings: Settings) -> ModelProviderStatus:
    provider = _normalize_provider(settings.embedding_provider)
    is_mock = provider in MOCK_EMBEDDING_PROVIDERS
    is_openai_compatible = provider in OPENAI_COMPATIBLE_PROVIDERS
    configured = is_mock or (
        is_openai_compatible
        and bool(settings.embedding_base_url.strip())
        and bool(settings.embedding_model_name.strip())
        and settings.embedding_dimension > 0
    )
    return ModelProviderStatus(
        provider=provider,
        model=settings.embedding_model_name,
        configured=configured,
        mock=is_mock,
        base_url_configured=bool(settings.embedding_base_url.strip()),
        api_key_configured=bool(settings.embedding_api_key.strip()),
        timeout_seconds=settings.embedding_timeout_seconds,
        dimension=settings.embedding_dimension,
    )


def _normalize_provider(provider: str) -> str:
    return provider.strip().lower() or "mock"
