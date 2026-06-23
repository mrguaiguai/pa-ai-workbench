"""Smoke-check M1 status response for WeKnora runtime visibility.

This fixture smoke covers P3-M1-E1:
- /api/status distinguishes mock, WeKnora missing config, and connected states;
- auth/workspace/kb config booleans are exposed without leaking token or endpoint;
- the response shape is suitable for the HomePage runtime status card.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app.api.health import api_status  # noqa: E402
from app.config import get_settings  # noqa: E402
from app import models as _models  # noqa: E402,F401
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the WeKnora status contract fails."""


def main() -> int:
    original_health = WeKnoraApiBackend.health
    WeKnoraApiBackend.health = lambda self: {"status": "ok"}  # type: ignore[assignment]
    original_env = dict(os.environ)
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora status E1 smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        get_settings.cache_clear()
        WeKnoraApiBackend.health = original_health  # type: ignore[assignment]
    print("WeKnora status E1 smoke passed (fixture)")
    print(f"- mock status: {result['mock_status']}")
    print(f"- missing config status: {result['missing_config_status']}")
    print(f"- connected status: {result['connected_status']}")
    print(f"- leaked secrets: {result['leaked_secrets']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        mock_status = _status_for(
            session,
            {
                "KNOWLEDGE_BACKEND": "mock",
                "MOCK_MODE": "true",
                "WEKNORA_BASE_URL": "",
                "WEKNORA_SERVICE_TOKEN": "",
                "WEKNORA_WORKSPACE_ID": "",
                "WEKNORA_DEFAULT_KB_ID": "",
            },
        )
        if mock_status.weknora.status != "mock":
            raise SmokeError(f"mock mode not identified: {mock_status.weknora}")
        if mock_status.weknora.connected:
            raise SmokeError("mock status unexpectedly marked WeKnora connected")

        missing_config = _status_for(
            session,
            {
                "KNOWLEDGE_BACKEND": "weknora_api",
                "MOCK_MODE": "false",
                "WEKNORA_BASE_URL": "",
                "WEKNORA_SERVICE_TOKEN": "",
                "WEKNORA_WORKSPACE_ID": "",
                "WEKNORA_DEFAULT_KB_ID": "",
            },
        )
        if missing_config.weknora.status != "missing_config":
            raise SmokeError(f"missing config not identified: {missing_config.weknora}")
        if missing_config.weknora.connected:
            raise SmokeError("missing config unexpectedly marked connected")

        missing_auth = _status_for(
            session,
            {
                "KNOWLEDGE_BACKEND": "weknora_api",
                "MOCK_MODE": "false",
                "WEKNORA_BASE_URL": "http://weknora.fixture/private",
                "WEKNORA_SERVICE_TOKEN": "",
                "WEKNORA_WORKSPACE_ID": "workspace-fixture",
                "WEKNORA_DEFAULT_KB_ID": "kb-fixture",
            },
        )
        if missing_auth.weknora.status != "missing_config":
            raise SmokeError(f"missing auth not identified: {missing_auth.weknora}")
        if missing_auth.weknora.service_token_configured:
            raise SmokeError("missing auth unexpectedly marked configured")

        connected = _status_for(
            session,
            {
                "KNOWLEDGE_BACKEND": "weknora_api",
                "MOCK_MODE": "false",
                "WEKNORA_BASE_URL": "http://weknora.fixture/private",
                "WEKNORA_SERVICE_TOKEN": "fixture-secret-token",
                "WEKNORA_WORKSPACE_ID": "workspace-fixture",
                "WEKNORA_DEFAULT_KB_ID": "kb-fixture",
            },
        )
        if connected.weknora.status != "connected":
            raise SmokeError(f"connected status not identified: {connected.weknora}")
        if not connected.weknora.service_token_configured:
            raise SmokeError("auth config boolean missing")
        if not connected.weknora.workspace_configured:
            raise SmokeError("workspace config boolean missing")
        if not connected.weknora.kb_configured:
            raise SmokeError("kb config boolean missing")

    response_text = connected.model_dump_json()
    leaked = [
        value
        for value in (
            "http://weknora.fixture/private",
            "fixture-secret-token",
            "workspace-fixture",
            "kb-fixture",
        )
        if value in response_text
    ]
    if leaked:
        raise SmokeError("status response leaked sensitive config: " + ", ".join(leaked))
    return {
        "mock_status": mock_status.weknora.status,
        "missing_config_status": missing_config.weknora.status,
        "connected_status": connected.weknora.status,
        "leaked_secrets": len(leaked),
    }


def _status_for(session: Session, env: dict[str, str]):
    for key, value in env.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
    get_settings.cache_clear()
    return api_status(session)


if __name__ == "__main__":
    raise SystemExit(main())
