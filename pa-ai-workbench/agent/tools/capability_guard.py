from __future__ import annotations

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.capabilities import backend_capability_snapshot
from knowledge_engine.capabilities import normalize_backend_name


class AgentCapabilityError(RuntimeError):
    """Raised when an Agent tool attempts an unsupported backend capability."""


class AgentCapabilityGuard:
    def __init__(self, knowledge_engine: KnowledgeEngine) -> None:
        self.knowledge_engine = knowledge_engine

    def require(self, capability: str) -> None:
        status = self._capabilities().get(capability, "unsupported")
        if status == "unsupported":
            raise AgentCapabilityError(
                f"Knowledge backend does not support capability: {capability}"
            )

    def _capabilities(self) -> dict[str, str]:
        health = self._health()
        raw_capabilities = health.get("capabilities") if isinstance(health, dict) else None
        if isinstance(raw_capabilities, dict):
            return {str(key): str(value) for key, value in raw_capabilities.items()}
        snapshot = backend_capability_snapshot(
            backend_name=self._backend_name_from_health(health),
            app_env=None,
            mock_mode=True,
            weknora_configured=None,
        )
        return dict(snapshot["capabilities"])

    def _health(self) -> dict:
        try:
            health = self.knowledge_engine.health()
        except Exception:  # noqa: BLE001
            return {}
        return health if isinstance(health, dict) else {}

    @staticmethod
    def _backend_name_from_health(health: dict) -> str:
        return normalize_backend_name(
            str(health.get("source") or health.get("backend") or "mock")
        )


__all__ = ["AgentCapabilityError", "AgentCapabilityGuard"]
