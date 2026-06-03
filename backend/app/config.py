from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "PA AI Workbench API"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "0.1.0"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    knowledge_backend: str = field(default_factory=lambda: os.getenv("KNOWLEDGE_BACKEND", "mock"))
    mock_mode: bool = field(default_factory=lambda: _get_bool("MOCK_MODE", True))
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/pa_workbench.db")
    )
    upload_dir: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "./uploads"))
    memory_recent_limit: int = field(default_factory=lambda: _get_int("MEMORY_RECENT_LIMIT", 10))
    chat_model_provider: str = field(
        default_factory=lambda: _get_str("CHAT_MODEL_PROVIDER", "mock")
    )
    chat_model_base_url: str = field(default_factory=lambda: os.getenv("CHAT_MODEL_BASE_URL", ""))
    chat_model_api_key: str = field(
        default_factory=lambda: os.getenv("CHAT_MODEL_API_KEY", ""),
        repr=False,
    )
    chat_model_name: str = field(default_factory=lambda: _get_str("CHAT_MODEL_NAME", "mock-chat"))
    chat_model_timeout_seconds: int = field(
        default_factory=lambda: _get_int("CHAT_MODEL_TIMEOUT_SECONDS", 60)
    )
    chat_model_temperature: float = field(
        default_factory=lambda: _get_float("CHAT_MODEL_TEMPERATURE", 0.2)
    )
    mock_model_mode: bool = field(default_factory=lambda: _get_bool("MOCK_MODEL_MODE", True))
    embedding_provider: str = field(
        default_factory=lambda: _get_str("EMBEDDING_PROVIDER", "mock")
    )
    embedding_base_url: str = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", ""))
    embedding_api_key: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY", ""),
        repr=False,
    )
    embedding_model_name: str = field(
        default_factory=lambda: _get_str("EMBEDDING_MODEL_NAME", "mock-embedding")
    )
    embedding_dimension: int = field(default_factory=lambda: _get_int("EMBEDDING_DIMENSION", 1024))
    embedding_timeout_seconds: int = field(
        default_factory=lambda: _get_int("EMBEDDING_TIMEOUT_SECONDS", 60)
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
