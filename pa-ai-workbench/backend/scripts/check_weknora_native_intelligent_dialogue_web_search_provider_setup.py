"""Live WNID-P4-01 Web Search provider setup check.

The script starts temporary PA backend/frontend services, proves PA exposes
confirmed native Web Search provider setup, creates or reuses a no-credential
DuckDuckGo provider, runs the saved-provider test when possible, and opens
`#/dialogue` in headless Chrome to verify the provider setup surface.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any
from urllib.parse import quote

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_intelligent_dialogue_shell import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_shell import _wait_for_dialogue_dom
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


MUTATION_CONFIRM_TOKEN = "MUTATE_NATIVE_WEB_SEARCH_PROVIDER"
TEST_CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER"
SAFE_PROVIDER = "duckduckgo"
SAFE_PROVIDER_NAME = "PA WNID DuckDuckGo Search"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-web-search-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'web-search.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            overview = _request_json(backend_port, "GET", "/api/web-search/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(_no_secret_payload(overview), "overview excludes secret-shaped fields")
            surfaces = _surfaces(overview)
            provider_types = _surface(surfaces, "provider_types")
            configured = _surface(surfaces, "configured_providers")
            mutations = _surface(surfaces, "mutations")
            setup = _surface(surfaces, "provider_setup")
            _assert(provider_types.get("status") == "live", "provider type catalog is live")
            _assert(int(provider_types.get("count") or 0) >= 1, "provider type catalog is non-empty")
            _assert(_has_duckduckgo_type(provider_types), "DuckDuckGo no-key provider type is available")
            _assert(configured.get("status") == "live", "configured provider list is live")
            _assert(mutations.get("status") == "live", "provider mutation surface is live")
            _assert(bool(mutations.get("confirmation")), "provider mutations advertise confirmation")
            _assert(setup.get("status") in {"live", "blocked"}, "provider setup surface is explicit")

            blocked_create = _request_json(
                backend_port,
                "POST",
                "/api/web-search/native/providers",
                {
                    "name": SAFE_PROVIDER_NAME,
                    "provider": SAFE_PROVIDER,
                    "description": "WNID-P4-01 no-credential provider setup",
                    "parameters": {},
                    "is_default": True,
                    "confirm_token": "wrong-token",
                },
            )
            blocked_mutation = _surface(_surfaces(blocked_create), "mutation")
            _assert(blocked_mutation.get("status") == "blocked", "bad provider setup token is blocked")

            provider_id = _find_provider_id(configured)
            created = False
            if not provider_id:
                created_response = _request_json(
                    backend_port,
                    "POST",
                    "/api/web-search/native/providers",
                    {
                        "name": SAFE_PROVIDER_NAME,
                        "provider": SAFE_PROVIDER,
                        "description": "WNID-P4-01 no-credential provider setup",
                        "parameters": {},
                        "is_default": True,
                        "confirm_token": MUTATION_CONFIRM_TOKEN,
                    },
                )
                _assert(_no_secret_payload(created_response), "create response excludes secrets")
                create_mutation = _surface(_surfaces(created_response), "mutation")
                _assert(create_mutation.get("status") == "live", "DuckDuckGo provider create is live")
                _assert(bool(create_mutation.get("success")), "DuckDuckGo provider create succeeded")
                provider_id = _provider_id_from_mutation(create_mutation)
                created = True

            _assert(bool(provider_id), "DuckDuckGo provider id is available")
            detail = _request_json(
                backend_port,
                "GET",
                f"/api/web-search/native/providers/{quote(provider_id, safe='')}",
            )
            _assert(_no_secret_payload(detail), "provider detail excludes secrets")
            read = _surface(_surfaces(detail), "provider_read")
            _assert(read.get("status") == "live", "provider read surface is live")

            test_response = _request_json(
                backend_port,
                "POST",
                f"/api/web-search/native/providers/{quote(provider_id, safe='')}/test",
                {"confirm_token": TEST_CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(test_response), "provider test response excludes secrets")
            test_surface = _surface(_surfaces(test_response), "provider_test")
            test_status = str(test_surface.get("status") or "")
            test_success = bool(test_surface.get("success"))
            _assert(test_status in {"live", "partial"}, "provider test result is explicit")

            audit_events = _request_json(
                backend_port,
                "GET",
                "/api/native-audit/events?capability=web_search&limit=20",
            )
            _assert(_audit_count(audit_events) >= 1, "web search provider setup/test audits are recorded")
            _assert(_no_secret_payload(audit_events), "web search audit response excludes secrets")

            refreshed = _request_json(backend_port, "GET", "/api/web-search/native/overview?limit=10")
            refreshed_surfaces = _surfaces(refreshed)
            refreshed_configured = _surface(refreshed_surfaces, "configured_providers")
            ready_count = int(refreshed_configured.get("ready_provider_count") or 0)
            _assert(ready_count >= 1, "at least one ready native Web Search provider is configured")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "Web Search Provider",
                "Setup DuckDuckGo",
                "Test provider",
                "provider_types",
                "configured",
                "provider_setup",
                "provider_test",
            )
            dom = _wait_for_dialogue_dom(frontend_port, temp_path / "chrome-profile", markers)
            _assert("高级工具" not in dom, "Web Search provider setup is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue Web Search provider panel does not render secrets")

            decision = "PASS" if test_success else "BLOCKED"
            blocker = "none" if test_success else str(test_surface.get("reason") or "native_web_search_provider_test_failed")
            print("WeKnora native intelligent dialogue Web Search provider setup")
            print(f"- decision: {decision}")
            print("- task: WNID-P4-01")
            print("- evidence_type: live_api + live_browser + audit + masked_provider_test")
            print(
                "- api: "
                f"provider={SAFE_PROVIDER} provider_id={provider_id} created={str(created).lower()} "
                f"ready_provider_count={ready_count} saved_test={test_status} success={str(test_success).lower()}"
            )
            print("- blocker: " + blocker)
            print("- browser: route=dialogue web_search_provider_setup=visible markers=8 hidden_advanced_panel=false")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _surfaces(payload: dict[str, Any]) -> dict[str, Any]:
    surfaces = payload.get("surfaces")
    _assert(isinstance(surfaces, dict), "surfaces object is present")
    return surfaces


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _has_duckduckgo_type(provider_types: dict[str, Any]) -> bool:
    items = provider_types.get("items") if isinstance(provider_types.get("items"), list) else []
    for item in items:
        if (
            isinstance(item, dict)
            and str(item.get("id") or "") == SAFE_PROVIDER
            and not bool(item.get("requires_api_key"))
        ):
            return True
    return False


def _find_provider_id(configured: dict[str, Any]) -> str:
    items = configured.get("items") if isinstance(configured.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("provider") or "") == SAFE_PROVIDER:
            provider_id = str(item.get("id") or "").strip()
            if provider_id:
                return provider_id
    return ""


def _provider_id_from_mutation(mutation: dict[str, Any]) -> str:
    result = mutation.get("result") if isinstance(mutation.get("result"), dict) else {}
    return str(result.get("id") or "").strip()


def _audit_count(payload: dict[str, Any]) -> int:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    return len(items)


def _no_secret_payload(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        '"api_key":',
        '"token":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"headers":',
        '"raw":',
        '"body":',
        '"payload":',
        '"base_url":',
        '"proxy_url":',
        '"private_key":',
    ]
    return not any(item in serialized for item in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
