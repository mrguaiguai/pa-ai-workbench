"""Live P3-M2-A5 smoke for PA real chat ModelGateway.

This script calls the configured chat provider through ModelGateway only. It
does not print API keys, full endpoints, prompts, or model response content.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402
from agent.model_gateway import ChatMessage  # noqa: E402
from agent.model_gateway import ChatMessageRole  # noqa: E402
from agent.model_gateway import ChatRequest  # noqa: E402
from agent.model_gateway import get_model_gateway  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the real chat smoke cannot prove release readiness."""


def main() -> int:
    settings = Settings()
    try:
        _validate_settings(settings)
        response = get_model_gateway().generate(
            ChatRequest(
                messages=[
                    ChatMessage(
                        role=ChatMessageRole.SYSTEM,
                        content="You are a concise release-readiness smoke responder.",
                    ),
                    ChatMessage(
                        role=ChatMessageRole.USER,
                        content=(
                            "Reply in one short Chinese sentence confirming that "
                            "the PA real chat smoke is using a live model."
                        ),
                    ),
                ],
                temperature=0.0,
                max_tokens=80,
                metadata={"smoke": "P3-M2-A5-real-chat"},
            )
        )
        _validate_response(settings, response)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "decision": "FAIL",
                    "reason": _safe_reason(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "decision": "PASS",
                "provider": response.provider,
                "model": response.model,
                "content_chars": len(response.content.strip()),
                "usage_keys": sorted(response.usage.keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _validate_settings(settings: Settings) -> None:
    missing: list[str] = []
    if settings.chat_model_provider.strip().lower() != "openai_compatible":
        missing.append("CHAT_MODEL_PROVIDER=openai_compatible")
    if settings.mock_model_mode:
        missing.append("MOCK_MODEL_MODE=false")
    if not settings.chat_model_base_url:
        missing.append("CHAT_MODEL_BASE_URL")
    if not settings.chat_model_api_key:
        missing.append("CHAT_MODEL_API_KEY")
    if not settings.chat_model_name:
        missing.append("CHAT_MODEL_NAME")
    if "deepseek" not in settings.chat_model_name.strip().lower():
        missing.append("CHAT_MODEL_NAME must be a DeepSeek model")
    if missing:
        raise SmokeError("missing or invalid required config: " + ", ".join(missing))


def _validate_response(settings: Settings, response) -> None:
    if response.provider != "openai_compatible":
        raise SmokeError(f"unexpected provider: {response.provider}")
    if "deepseek" not in response.model.lower() and "deepseek" not in settings.chat_model_name.lower():
        raise SmokeError(f"unexpected model: {response.model}")
    if not response.content.strip():
        raise SmokeError("model returned empty content")


def _safe_reason(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    for marker in ("Authorization", "Bearer", "api_key", "token", "secret", "password"):
        text = text.replace(marker, "[redacted]")
    return " ".join(text.split())[:300]


if __name__ == "__main__":
    raise SystemExit(main())
