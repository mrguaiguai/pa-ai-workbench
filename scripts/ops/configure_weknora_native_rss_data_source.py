"""Configure a safe no-credential native RSS data source for WNX validation.

This script uses PA's WeKnora adapter against the live native API. It prints
only sanitized status/count evidence and never prints service tokens, native
IDs, feed URLs, resource names, raw configs, payloads, or sync logs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


DEFAULT_FEED_URL = "https://www.rfc-editor.org/rfcrss.xml"
SOURCE_NAME = "WNX RSS connector smoke"


class ConfigureError(RuntimeError):
    """Raised when a safe configured RSS data source cannot be proven."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help="Public http(s) RSS/Atom feed URL. The value is not printed.",
    )
    args = parser.parse_args()

    settings = Settings()
    try:
        _validate_settings(settings)
        backend = _backend(settings)
        result = _configure_rss_source(backend, str(args.feed_url or "").strip())
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native RSS data source configuration failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora native RSS data source configured")
    print("- decision: PASS")
    print("- evidence_type: live_api_current_run")
    print(f"- connector_registered: {str(result['connector_registered']).lower()}")
    print(f"- rss_source: {result['rss_source']}")
    print(f"- data_sources: count={result['data_source_count']} rss_count={result['rss_count']}")
    print(
        "- validation: status={status} connected={connected}".format(
            status=result["validation_status"],
            connected=str(result["connected"]).lower(),
        )
    )
    print(
        "- resources: status={status} count={count}".format(
            status=result["resources_status"],
            count=result["resource_count"],
        )
    )
    return 0


def _validate_settings(settings: Settings) -> None:
    missing: list[str] = []
    if settings.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if settings.mock_mode:
        missing.append("MOCK_MODE=false")
    if not settings.weknora_base_url or settings.weknora_base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if not settings.weknora_service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not settings.weknora_default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if missing:
        raise ConfigureError("missing or invalid required env: " + ", ".join(missing))


def _backend(settings: Settings) -> WeKnoraApiBackend:
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )


def _configure_rss_source(backend: WeKnoraApiBackend, feed_url: str) -> dict[str, Any]:
    if not feed_url.startswith(("http://", "https://")):
        raise ConfigureError("RSS feed URL must use http or https")

    connector_types = backend.list_data_source_connector_types()
    connector_registered = any(item.get("type") == "rss" for item in connector_types)
    if not connector_registered:
        raise ConfigureError("native RSS connector is not registered")

    data_sources = backend.list_data_sources(include_internal_refs=True)
    rss_sources = [item for item in data_sources if item.get("type") == "rss"]
    selected = _first_operable_rss_source(rss_sources)
    rss_source_state = "existing"
    if selected is None:
        backend.create_rss_data_source(feed_url=feed_url, name=SOURCE_NAME)
        data_sources = backend.list_data_sources(include_internal_refs=True)
        rss_sources = [item for item in data_sources if item.get("type") == "rss"]
        selected = _first_operable_rss_source(rss_sources)
        rss_source_state = "created"
    if selected is None:
        raise ConfigureError("RSS data source was not available after configuration")

    data_source_ref = str(selected.get("_native_data_source_id") or "").strip()
    if not data_source_ref:
        raise ConfigureError("RSS data source reference is unavailable")
    validation = backend.validate_data_source(data_source_ref)
    resources = backend.list_data_source_resources(data_source_ref)
    if not validation.get("connected"):
        raise ConfigureError("RSS data source validation is not connected")
    if int(resources.get("count") or 0) <= 0:
        raise ConfigureError("RSS resource probe returned no resources")

    return {
        "connector_registered": connector_registered,
        "rss_source": rss_source_state,
        "data_source_count": len(data_sources),
        "rss_count": len(rss_sources),
        "validation_status": validation.get("status") or "connected",
        "connected": bool(validation.get("connected")),
        "resources_status": "live",
        "resource_count": int(resources.get("count") or 0),
    }


def _first_operable_rss_source(data_sources: list[dict]) -> dict | None:
    for item in data_sources:
        if item.get("_native_data_source_id") and item.get("resource_count"):
            return item
    return None


def _safe_reason(exc: Exception) -> str:
    text = str(exc).strip().replace("\n", " ")
    forbidden_markers = ("token", "authorization", "password", "secret", "api_key")
    lowered = text.lower()
    if any(marker in lowered for marker in forbidden_markers) or "http://" in lowered or "https://" in lowered:
        return exc.__class__.__name__
    return text[:180] or exc.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
