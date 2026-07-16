"""Live WNFC-P2-01 native MCP CRUD and credential smoke.

The script creates a temporary native MCP service through the PA BFF, updates it
to disabled state, writes and clears credentials through the native credential
subresource, verifies PA responses stay masked, records NativeMutationAudit
events, and deletes the temporary service before exit. It does not execute MCP
tools or probe the configured URL.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
from typing import Any
from urllib.parse import quote

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_json


CONFIRM_TOKEN = "CONFIRM_NATIVE_MCP_MUTATION"
SERVICE_URL = "https://example.com/mcp"


def main() -> int:
    backend_port = _free_port()
    created_service_id = ""
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-mcp-crud-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'mcp-crud.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, None)
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview_before = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            _assert(overview_before.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview_before.get("masked")), "overview is masked")

            suffix = str(int(time.time()))
            service_name = f"wnfc-p2-01-temp-{suffix}"
            create = _request_json(
                backend_port,
                "POST",
                "/api/mcp/native/services",
                {
                    "name": service_name,
                    "description": "WNFC-P2-01 temporary disabled CRUD evidence service.",
                    "enabled": False,
                    "transport_type": "http-streamable",
                    "url": SERVICE_URL,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_mutation_succeeded(create, "create"), "create mutation succeeded")
            _assert(_no_secret_payload(create), "create response excludes raw secret-shaped fields")
            created = _mutation_result(create)
            created_service_id = str(created.get("id") or "")
            _assert(bool(created_service_id), "created service id is returned")
            _assert(created.get("name") == service_name, "created service name is visible")

            detail = _request_json(
                backend_port,
                "GET",
                f"/api/mcp/native/services/{quote(created_service_id, safe='')}",
            )
            _assert(_service_read_succeeded(detail), "created service is readable through PA")
            _assert(_no_secret_payload(detail), "detail excludes native URL/header/auth payload")

            updated_name = f"{service_name}-updated"
            update = _request_json(
                backend_port,
                "PUT",
                f"/api/mcp/native/services/{quote(created_service_id, safe='')}",
                {
                    "name": updated_name,
                    "description": "WNFC-P2-01 updated temporary service.",
                    "enabled": False,
                    "transport_type": "http-streamable",
                    "url": SERVICE_URL,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_mutation_succeeded(update, "update"), "update mutation succeeded")
            _assert(_mutation_result(update).get("name") == updated_name, "update result has updated name")
            _assert(_mutation_result(update).get("enabled") is False, "updated service is disabled")
            _assert(_no_secret_payload(update), "update response excludes raw secret-shaped fields")

            raw_credential = f"wnfc-secret-value-{suffix}"
            credentials = _request_json(
                backend_port,
                "PUT",
                f"/api/mcp/native/services/{quote(created_service_id, safe='')}/credentials",
                {
                    "api_key": raw_credential,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_mutation_succeeded(credentials, "credentials_update"), "credential mutation succeeded")
            credential_result = _mutation_result(credentials)
            _assert(credential_result.get("masked") is True, "credential response is masked")
            _assert(int(credential_result.get("configured_field_count") or 0) >= 1, "credential metadata reports configured field")
            _assert(raw_credential not in json.dumps(credentials, ensure_ascii=False), "raw credential absent from response")
            _assert(_no_secret_payload(credentials), "credential response excludes raw secret-shaped fields")

            detail_with_credential = _request_json(
                backend_port,
                "GET",
                f"/api/mcp/native/services/{quote(created_service_id, safe='')}",
            )
            service_item = _service_read_item(detail_with_credential)
            _assert(service_item.get("credentials_configured") is True, "detail reports credential configured")
            _assert(int(service_item.get("configured_credential_field_count") or 0) >= 1, "detail counts configured credential")
            _assert(raw_credential not in json.dumps(detail_with_credential, ensure_ascii=False), "raw credential absent from detail")
            _assert(_no_secret_payload(detail_with_credential), "detail with credential remains masked")

            cleared = _request_json(
                backend_port,
                "DELETE",
                f"/api/mcp/native/services/{quote(created_service_id, safe='')}/credentials/api_key",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_mutation_succeeded(cleared, "credentials_clear"), "credential clear mutation succeeded")
            _assert(_mutation_result(cleared).get("cleared") is True, "credential clear result is explicit")
            _assert(_no_secret_payload(cleared), "credential clear response remains masked")

            delete = _request_json(
                backend_port,
                "DELETE",
                f"/api/mcp/native/services/{quote(created_service_id, safe='')}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_mutation_succeeded(delete, "delete"), "delete mutation succeeded")
            _assert(_no_secret_payload(delete), "delete response remains masked")

            overview_after = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            after_items = _services_items(overview_after)
            _assert(
                all(item.get("id") != created_service_id for item in after_items),
                "temporary MCP service is removed from PA overview",
            )

            audits = _request_json(backend_port, "GET", "/api/native-audit/events?capability=mcp&limit=20")
            _assert(_audit_log_contains(audits), "native audit log contains MCP CRUD/credential operations")
            _assert(_no_secret_payload(audits), "audit API excludes raw secrets")

            print("WeKnora native MCP CRUD and credentials")
            print("- decision: PASS")
            print("- evidence_type: live api plus audit proof")
            print("- service_crud: create=live read=live update=live delete=live")
            print("- credentials: update=masked_live clear=live")
            print("- audit: mcp mutation events recorded")
            print("- cleanup: temporary native MCP service deleted")
            return 0
        finally:
            if created_service_id:
                _best_effort_delete(backend_port, created_service_id)
            _terminate(backend)


def _mutation_succeeded(response: dict[str, Any], action: str) -> bool:
    surfaces = response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {}
    surface = _surface(surfaces, "mutation")
    audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
    return (
        response.get("schema_version") == "wnfc-p2-01-mcp-mutation"
        and surface.get("status") == "live"
        and surface.get("action") == action
        and surface.get("success") is True
        and audit.get("capability") == "mcp"
        and audit.get("status") == "succeeded"
    )


def _mutation_result(response: dict[str, Any]) -> dict[str, Any]:
    surfaces = response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {}
    surface = _surface(surfaces, "mutation")
    result = surface.get("result")
    _assert(isinstance(result, dict), "mutation result is present")
    return result


def _service_read_succeeded(response: dict[str, Any]) -> bool:
    service_read = _surface(
        response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {},
        "service_read",
    )
    return response.get("schema_version") == "wnx-p2-02-service" and service_read.get("status") == "live"


def _service_read_item(response: dict[str, Any]) -> dict[str, Any]:
    service_read = _surface(
        response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {},
        "service_read",
    )
    item = service_read.get("item")
    _assert(isinstance(item, dict), "service read item is present")
    return item


def _services_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces = response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {}
    services = _surface(surfaces, "services")
    items = services.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _audit_log_contains(response: dict[str, Any]) -> bool:
    items = response.get("items")
    if not isinstance(items, list):
        return False
    operations = {
        str(item.get("operation") or "")
        for item in items
        if isinstance(item, dict) and item.get("status") == "succeeded"
    }
    return {
        "weknora_mcp_service_create",
        "weknora_mcp_service_update",
        "weknora_mcp_credentials_update",
        "weknora_mcp_credentials_clear",
        "weknora_mcp_service_delete",
    } <= operations


def _no_secret_payload(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        "wnfc-secret-value",
        '"api_key":',
        '"token":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"headers":',
        '"auth_config":',
        '"url":',
        '"env_vars":',
        '"stdio_config":',
    ]
    return not any(token in serialized for token in forbidden)


def _best_effort_delete(port: int, service_id: str) -> None:
    try:
        _request_json(
            port,
            "DELETE",
            f"/api/mcp/native/services/{quote(service_id, safe='')}",
            {"confirm_token": CONFIRM_TOKEN},
        )
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
