from dataclasses import dataclass
from dataclasses import field
import os

from agent.model_gateway.base import ModelGateway


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


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
class ModelGatewayConfig:
    provider: str = field(default_factory=lambda: _get_str("CHAT_MODEL_PROVIDER", "mock"))
    base_url: str = field(default_factory=lambda: os.getenv("CHAT_MODEL_BASE_URL", ""))
    api_key: str = field(
        default_factory=lambda: os.getenv("CHAT_MODEL_API_KEY", ""),
        repr=False,
    )
    model_name: str = field(default_factory=lambda: _get_str("CHAT_MODEL_NAME", "mock-chat"))
    timeout_seconds: int = field(
        default_factory=lambda: _get_int("CHAT_MODEL_TIMEOUT_SECONDS", 60)
    )
    temperature: float = field(
        default_factory=lambda: _get_float("CHAT_MODEL_TEMPERATURE", 0.2)
    )
    mock_model_mode: bool = field(default_factory=lambda: _get_bool("MOCK_MODEL_MODE", True))


def get_model_gateway(config: ModelGatewayConfig | None = None) -> ModelGateway:
    resolved = config or ModelGatewayConfig()
    provider = resolved.provider.strip().lower()
    if provider in {"mock", "mock_chat"}:
        from agent.model_gateway.providers.mock import MockChatProvider

        return MockChatProvider(resolved)

    raise NotImplementedError(
        f"Chat model provider is not implemented yet: {resolved.provider}. "
        "G5 adds the OpenAI-compatible provider."
    )
