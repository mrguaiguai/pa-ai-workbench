"""Live WNFC-P3-04 vector-store full-management smoke.

This smoke proves the real native/PA vector-store path: masked native
type/list/detail read, active KB binding, embedding compatibility, confirmed
saved/env store test, confirmed raw Qdrant test, confirmed user-store
create/update/delete, NativeMutationAudit, and browser status proof.

It does not create fake vector stores. The raw connection config is sent only to
the local PA BFF during the live test and is never printed or expected in API
responses/audit summaries. Native KB vector_store_id remains immutable after
creation, so PA surfaces that native contract instead of faking KB rebind.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_kb_management import CHROME_BIN
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _read_dom_text_via_cdp
from check_weknora_native_kb_management import _request_chrome_json
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_chrome
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


CONFIRM_TOKEN = "TEST_NATIVE_VECTOR_STORE"
CONFIRM_RAW_TOKEN = "TEST_NATIVE_VECTOR_STORE_RAW"
CONFIRM_MANAGE_TOKEN = "MANAGE_NATIVE_VECTOR_STORE"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-vector-store-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'vector-store-p3-04.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/vector-stores/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(_no_secret_payload(overview), "overview excludes raw config and credentials")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            store_types = _surface(surfaces, "store_types")
            stores = _surface(surfaces, "stores")
            store_read = _surface(surfaces, "store_read")
            store_test = _surface(surfaces, "store_test")
            kb_binding = _surface(surfaces, "kb_binding")
            embedding = _surface(surfaces, "embedding")
            compatibility = _surface(surfaces, "embedding_compatibility")
            mutations = _surface(surfaces, "mutations")
            original_user_count = int(stores.get("user_count") or 0)

            _assert(store_types.get("status") == "live", "store type catalog is live")
            _assert(int(store_types.get("count") or 0) > 0, "store type catalog is non-empty")
            _assert(stores.get("status") == "live", "store list is live")
            _assert(int(stores.get("count") or 0) > 0, "at least one native store is configured")
            _assert(store_read.get("status") == "live", "store read surface is live")
            _assert(store_test.get("status") == "blocked", "store test is confirmation-gated by default")
            _assert(embedding.get("status") == "live", "embedding readiness is live")
            _assert(embedding.get("mock") is False, "embedding is not mock")
            _assert(compatibility.get("status") == "live", "embedding compatibility is live")
            _assert(kb_binding.get("status") == "live", "active KB binding is live")
            _assert(mutations.get("status") == "live", "full mutation lane is live")
            _assert(_item_status_present(mutations, "raw connection test/create", "live"), "raw create/test live")
            _assert(
                _item_status_present(mutations, "KB vector-store rebind", "native_immutable"),
                "KB rebind is surfaced as native immutable",
            )

            items = stores.get("items") if isinstance(stores.get("items"), list) else []
            first = items[0] if items and isinstance(items[0], dict) else {}
            store_index = int(first.get("safe_index") or 0)
            _assert("id" not in first and "_native_store_id" not in first, "store item hides raw native id")

            detail = _request_json(
                backend_port,
                "GET",
                f"/api/vector-stores/native/stores/by-index/{store_index}",
            )
            _assert(_no_secret_payload(detail), "detail excludes raw config and credentials")
            detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
            _assert(_surface(detail_surfaces, "store_read").get("status") == "live", "detail read is live")
            _assert(_surface(detail_surfaces, "store_test").get("status") == "blocked", "detail test is gated")

            blocked = _request_json(
                backend_port,
                "POST",
                f"/api/vector-stores/native/stores/by-index/{store_index}/test",
                {"confirm_token": "WRONG"},
            )
            _assert(_no_secret_payload(blocked), "blocked test response is sanitized")
            blocked_test = _surface(
                blocked.get("surfaces") if isinstance(blocked.get("surfaces"), dict) else {},
                "store_test",
            )
            _assert(blocked_test.get("status") == "blocked", "wrong token blocks test")

            confirmed = _request_json(
                backend_port,
                "POST",
                f"/api/vector-stores/native/stores/by-index/{store_index}/test",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(confirmed), "confirmed test response is sanitized")
            confirmed_test = _surface(
                confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {},
                "store_test",
            )
            _assert(confirmed_test.get("status") == "live", "confirmed native vector store test is live")
            audit = confirmed.get("audit") if isinstance(confirmed.get("audit"), dict) else {}
            _assert(audit.get("operation") == "weknora_vector_store_test", "vector test audit operation recorded")
            _assert(audit.get("status") == "succeeded", "vector test audit succeeded")
            _assert(audit.get("confirm_token_id") == "native_vector_store_test", "audit stores token id only")

            qdrant_config = _qdrant_test_config()
            raw_blocked = _request_json(
                backend_port,
                "POST",
                "/api/vector-stores/native/raw-test",
                {**qdrant_config, "confirm_token": "WRONG"},
            )
            _assert(_no_secret_payload(raw_blocked), "blocked raw test response is sanitized")
            _assert(
                _surface(
                    raw_blocked.get("surfaces") if isinstance(raw_blocked.get("surfaces"), dict) else {},
                    "raw_test",
                ).get("status")
                == "blocked",
                "wrong token blocks raw vector store test",
            )

            raw_confirmed = _request_json(
                backend_port,
                "POST",
                "/api/vector-stores/native/raw-test",
                {**qdrant_config, "confirm_token": CONFIRM_RAW_TOKEN},
            )
            _assert(_no_secret_payload(raw_confirmed), "confirmed raw test response is sanitized")
            raw_test = _surface(
                raw_confirmed.get("surfaces") if isinstance(raw_confirmed.get("surfaces"), dict) else {},
                "raw_test",
            )
            _assert(raw_test.get("status") == "live", "confirmed raw Qdrant test is live")
            raw_audit = raw_confirmed.get("audit") if isinstance(raw_confirmed.get("audit"), dict) else {}
            _assert(raw_audit.get("operation") == "weknora_vector_store_raw_test", "raw test audit recorded")
            _assert(raw_audit.get("status") == "succeeded", "raw test audit succeeded")

            create_blocked = _request_json(
                backend_port,
                "POST",
                "/api/vector-stores/native/stores",
                {**_store_create_payload(), "confirm_token": "WRONG"},
            )
            _assert(_no_secret_payload(create_blocked), "blocked create response is sanitized")
            _assert(
                _surface(
                    create_blocked.get("surfaces") if isinstance(create_blocked.get("surfaces"), dict) else {},
                    "store_create",
                ).get("status")
                == "blocked",
                "wrong token blocks vector store create",
            )

            created_index: int | None = None
            create_audit: dict[str, Any] = {}
            try:
                created = _request_json(
                    backend_port,
                    "POST",
                    "/api/vector-stores/native/stores",
                    {**_store_create_payload(), "confirm_token": CONFIRM_MANAGE_TOKEN},
                )
                _assert(_no_secret_payload(created), "create response is sanitized")
                create_surface = _surface(
                    created.get("surfaces") if isinstance(created.get("surfaces"), dict) else {},
                    "store_create",
                )
                _assert(create_surface.get("status") == "live", "user vector store create is live")
                created_index = int(create_surface.get("safe_index"))
                create_audit = created.get("audit") if isinstance(created.get("audit"), dict) else {}
                _assert(create_audit.get("operation") == "weknora_vector_store_create", "create audit recorded")
                _assert(create_audit.get("status") == "succeeded", "create audit succeeded")

                after_create = _request_json(backend_port, "GET", "/api/vector-stores/native/overview?limit=10")
                _assert(_no_secret_payload(after_create), "post-create overview is sanitized")
                after_create_surfaces = after_create.get("surfaces") if isinstance(after_create.get("surfaces"), dict) else {}
                after_create_stores = _surface(after_create_surfaces, "stores")
                _assert(
                    int(after_create_stores.get("user_count") or 0) == original_user_count + 1,
                    "created user vector store is listed",
                )

                updated = _request_json(
                    backend_port,
                    "PUT",
                    f"/api/vector-stores/native/stores/by-index/{created_index}",
                    {"name": _store_update_name(), "confirm_token": CONFIRM_MANAGE_TOKEN},
                )
                _assert(_no_secret_payload(updated), "update response is sanitized")
                update_surface = _surface(
                    updated.get("surfaces") if isinstance(updated.get("surfaces"), dict) else {},
                    "store_update",
                )
                _assert(update_surface.get("status") == "live", "user vector store update is live")
                update_audit = updated.get("audit") if isinstance(updated.get("audit"), dict) else {}
                _assert(update_audit.get("operation") == "weknora_vector_store_update", "update audit recorded")
                _assert(update_audit.get("status") == "succeeded", "update audit succeeded")

                created_test = _request_json(
                    backend_port,
                    "POST",
                    f"/api/vector-stores/native/stores/by-index/{created_index}/test",
                    {"confirm_token": CONFIRM_TOKEN},
                )
                _assert(_no_secret_payload(created_test), "created store test response is sanitized")
                created_test_surface = _surface(
                    created_test.get("surfaces") if isinstance(created_test.get("surfaces"), dict) else {},
                    "store_test",
                )
                _assert(created_test_surface.get("status") == "live", "created user store test is live")
                created_test_audit = created_test.get("audit") if isinstance(created_test.get("audit"), dict) else {}
                _assert(created_test_audit.get("status") == "succeeded", "created store test audit succeeded")
            finally:
                if created_index is not None:
                    deleted = _request_json(
                        backend_port,
                        "DELETE",
                        f"/api/vector-stores/native/stores/by-index/{created_index}",
                        {"confirm_token": CONFIRM_MANAGE_TOKEN},
                    )
                    _assert(_no_secret_payload(deleted), "delete response is sanitized")
                    delete_surface = _surface(
                        deleted.get("surfaces") if isinstance(deleted.get("surfaces"), dict) else {},
                        "store_delete",
                    )
                    _assert(delete_surface.get("status") == "live", "user vector store delete is live")
                    delete_audit = deleted.get("audit") if isinstance(deleted.get("audit"), dict) else {}
                    _assert(delete_audit.get("operation") == "weknora_vector_store_delete", "delete audit recorded")
                    _assert(delete_audit.get("status") == "succeeded", "delete audit succeeded")

            final_overview = _request_json(backend_port, "GET", "/api/vector-stores/native/overview?limit=10")
            _assert(_no_secret_payload(final_overview), "final overview is sanitized")
            final_surfaces = final_overview.get("surfaces") if isinstance(final_overview.get("surfaces"), dict) else {}
            final_stores = _surface(final_surfaces, "stores")
            _assert(
                int(final_stores.get("user_count") or 0) == original_user_count,
                "temporary user vector store is cleaned up",
            )

            audit_events = _request_json(
                backend_port,
                "GET",
                "/api/native-audit/events?capability=vector_store&limit=10",
            )
            _assert(_audit_log_contains(audit_events, audit.get("id")), "audit API includes vector-store test event")
            _assert(_audit_log_contains(audit_events, raw_audit.get("id")), "audit API includes raw test event")
            _assert(_audit_log_contains(audit_events, create_audit.get("id")), "audit API includes create event")
            _assert(_no_raw_confirm_token_in_audit(audit_events), "audit API does not return raw confirm token")
            _assert(_no_secret_payload(audit_events), "audit API excludes raw vector config")

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=20")
            _assert(_no_secret_payload(native_status), "native status is sanitized")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            vector_group = groups.get("vector_store") if isinstance(groups.get("vector_store"), dict) else {}
            summary = vector_group.get("summary") if isinstance(vector_group.get("summary"), dict) else {}
            _assert(vector_group.get("status") == "live", "status center marks vector store live")
            _assert(summary.get("store_test_status") == "blocked", "status center exposes gated test status")
            _assert(summary.get("mutations_status") == "live", "status center exposes live mutation lane")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "Vector store",
                    "store_test_status: blocked",
                    "mutations_status: live",
                    "/api/vector-stores/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native vector-store full management")
            print("- decision: PASS")
            print(
                "- evidence_type: live api/browser plus docker runtime plus audit proof"
                if browser_mode
                else "- evidence_type: live api plus docker runtime plus audit proof"
            )
            print(
                "- store_types: status={status} count={count}".format(
                    status=store_types.get("status"),
                    count=int(store_types.get("count") or 0),
                )
            )
            print(
                "- stores: status={status} count={count} env={env} user={user}".format(
                    status=stores.get("status"),
                    count=int(stores.get("count") or 0),
                    env=int(stores.get("env_count") or 0),
                    user=int(stores.get("user_count") or 0),
                )
            )
            print("- safe_test: confirmed=live audit=succeeded")
            print("- raw_test: confirmed=live engine=qdrant")
            print("- user_store_crud: create=live update=live test=live delete=live")
            print(
                "- embedding_compatibility: status={status} dimension={dimension} kb_source={source}".format(
                    status=compatibility.get("status"),
                    dimension=compatibility.get("embedding_dimension"),
                    source=compatibility.get("kb_binding_source") or "unknown",
                )
            )
            print("- native_immutable: kb_rebind")
            if browser_mode:
                print("- browser: Capability Center rendered vector-store live/status proof")
            print("- output: sanitized")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _item_status_present(surface: dict[str, Any], name: str, status: str) -> bool:
    items = surface.get("items") if isinstance(surface.get("items"), list) else []
    return any(
        isinstance(item, dict)
        and item.get("name") == name
        and item.get("status") == status
        for item in items
    )


def _audit_log_contains(response: dict[str, Any], audit_id: object) -> bool:
    items = response.get("items") if isinstance(response.get("items"), list) else []
    return any(isinstance(item, dict) and item.get("id") == audit_id for item in items)


def _no_raw_confirm_token_in_audit(response: dict[str, Any]) -> bool:
    serialized = json.dumps(response, ensure_ascii=False, sort_keys=True)
    return (
        CONFIRM_TOKEN not in serialized
        and CONFIRM_RAW_TOKEN not in serialized
        and CONFIRM_MANAGE_TOKEN not in serialized
    )


def _no_secret_payload(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        '"_native_store_id":',
        '"tenant_id":',
        '"connection_config":',
        '"index_config":',
        '"addr":',
        '"host":',
        '"port":',
        '"username":',
        '"password":',
        '"api_key":',
        '"authorization":',
        '"secret":',
        '"database":',
        '"dsn":',
        '"endpoint":',
        '"base_url":',
        '"collection":',
        '"index_name":',
        '"payload":',
    ]
    return not any(token in serialized for token in forbidden)


def _qdrant_test_config() -> dict[str, Any]:
    host = os.getenv("WNFC_QDRANT_HOST", "pa-wnfc-qdrant")
    port = int(os.getenv("WNFC_QDRANT_GRPC_PORT", "6334"))
    return {
        "engine_type": "qdrant",
        "connection_config": {
            "host": host,
            "port": port,
            "use_tls": False,
        },
    }


def _store_create_payload() -> dict[str, Any]:
    return {
        **_qdrant_test_config(),
        "name": _store_create_name(),
        "index_config": {
            "collection_prefix": _collection_prefix(),
            "shard_number": 1,
            "replication_factor": 1,
        },
    }


def _collection_prefix() -> str:
    return "pa_wnfc_p3_04"


def _store_create_name() -> str:
    return "PA WNFC P3-04 Qdrant"


def _store_update_name() -> str:
    return "PA WNFC P3-04 Qdrant Updated"


def _dump_capability_dom(port: int, user_data_dir: Path) -> str:
    if not CHROME_BIN.exists():
        raise RuntimeError("Google Chrome executable not found")
    debug_port = _free_port()
    chrome = subprocess.Popen(
        [
            str(CHROME_BIN),
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-first-run",
            f"--user-data-dir={user_data_dir}",
            f"--remote-debugging-port={debug_port}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_for_chrome(debug_port)
        target = _request_chrome_json(
            debug_port,
            "PUT",
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/capabilities', safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        dom = ""
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if "Vector store" in dom and "mutations_status: live" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
