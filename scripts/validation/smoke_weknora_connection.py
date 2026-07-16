"""Smoke-check PA's WeKnora service-account connection.

Checks are intentionally read-only:
- health: GET /health
- auth: GET /api/v1/auth/me
- workspace: GET /api/v1/tenants/{WEKNORA_WORKSPACE_ID}
- knowledge base: GET /api/v1/knowledge-bases/{WEKNORA_DEFAULT_KB_ID}

The script never uploads files and never prints service tokens.

For local validation without a live WeKnora instance, set:
    WEKNORA_BASE_URL=fixture://weknora
    WEKNORA_SERVICE_TOKEN=fixture-token
    WEKNORA_WORKSPACE_ID=10000
    WEKNORA_DEFAULT_KB_ID=kb-fixture
This fixture mode is explicit and reports itself as fixture, not live.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when a smoke step fails with a clear operator-facing message."""


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    service_token: str
    workspace_id: str
    default_kb_id: str
    timeout_seconds: int

    @classmethod
    def from_settings(cls) -> "SmokeConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            workspace_id=settings.weknora_workspace_id,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
        )

    @property
    def fixture_mode(self) -> bool:
        return urlparse(self.base_url).scheme == "fixture"


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        if config.fixture_mode:
            result = _run_fixture_smoke(config)
        else:
            result = _run_live_smoke(config)
    except SmokeError as exc:
        print(f"WeKnora connection smoke failed: {exc}", file=sys.stderr)
        return 1

    mode = "fixture" if config.fixture_mode else "live"
    print(f"WeKnora connection smoke passed ({mode})")
    print(f"- base URL: {config.base_url}")
    print(f"- auth ok: {result['auth']}")
    print(f"- workspace/kb ok: {result['workspace']} / {result['knowledge_base']}")
    return 0


def _validate_config(config: SmokeConfig) -> None:
    missing = []
    if not config.base_url:
        missing.append("WEKNORA_BASE_URL")
    if not config.service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not config.workspace_id:
        missing.append("WEKNORA_WORKSPACE_ID")
    if not config.default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if config.timeout_seconds <= 0:
        missing.append("WEKNORA_TIMEOUT_SECONDS")
    if missing:
        raise SmokeError("missing required env: " + ", ".join(missing))


def _run_fixture_smoke(config: SmokeConfig) -> dict[str, str]:
    if config.service_token == "fixture-token":
        return {
            "health": "ok",
            "auth": "ok",
            "workspace": config.workspace_id,
            "knowledge_base": config.default_kb_id,
        }
    raise SmokeError("fixture mode requires WEKNORA_SERVICE_TOKEN=fixture-token")


def _run_live_smoke(config: SmokeConfig) -> dict[str, str]:
    health = _request_json(config, "GET", "/health")
    status = _json_get(health, "status", default="ok")
    if str(status).lower() not in {"ok", "healthy", "success"}:
        raise SmokeError(f"health returned unexpected status: {status}")

    auth = _request_json(config, "GET", "/api/v1/auth/me", authenticated=True)
    if not _is_success(auth):
        raise SmokeError("auth check did not return success=true")

    workspace = _request_json(
        config,
        "GET",
        f"/api/v1/tenants/{config.workspace_id}",
        authenticated=True,
    )
    if not _is_success(workspace):
        raise SmokeError("workspace check did not return success=true")

    kb = _request_json(
        config,
        "GET",
        f"/api/v1/knowledge-bases/{config.default_kb_id}",
        authenticated=True,
    )
    if not _is_success(kb):
        raise SmokeError("knowledge-base check did not return success=true")

    return {
        "health": str(status),
        "auth": _describe_user(auth),
        "workspace": _describe_data(workspace, fallback=config.workspace_id),
        "knowledge_base": _describe_data(kb, fallback=config.default_kb_id),
    }


def _request_json(
    config: SmokeConfig,
    method: str,
    path: str,
    authenticated: bool = False,
) -> Any:
    headers = {"Accept": "application/json"}
    if authenticated:
        headers["X-API-Key"] = config.service_token
        headers["Authorization"] = f"Bearer {config.service_token}"
        if config.workspace_id.isdigit():
            headers["X-Tenant-ID"] = config.workspace_id

    request = Request(
        url=f"{config.base_url}{path}",
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"{method} {path} returned HTTP {exc.code}: {_shorten(body)}") from exc
    except (TimeoutError, URLError) as exc:
        raise SmokeError(f"{method} {path} failed: {exc}") from exc

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SmokeError(f"{method} {path} returned invalid JSON") from exc


def _is_success(value: Any) -> bool:
    return isinstance(value, dict) and value.get("success") is True


def _json_get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return default


def _describe_user(value: Any) -> str:
    if not isinstance(value, dict):
        return "ok"
    data = value.get("data")
    if not isinstance(data, dict):
        return "ok"
    user = data.get("user")
    if isinstance(user, dict):
        return str(user.get("email") or user.get("username") or user.get("id") or "ok")
    return "ok"


def _describe_data(value: Any, fallback: str) -> str:
    if not isinstance(value, dict):
        return fallback
    data = value.get("data")
    if isinstance(data, dict):
        return str(data.get("name") or data.get("title") or data.get("id") or fallback)
    return fallback


def _shorten(value: str, limit: int = 240) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
