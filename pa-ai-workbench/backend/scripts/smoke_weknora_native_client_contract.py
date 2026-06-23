"""Fixture smoke for WNX-P0-01 shared WeKnora native client contract.

This smoke does not read .env and does not call live WeKnora. It proves that
existing native adapter methods route through one client object and that the
client status/error contract does not expose secret config values.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraNativeClient  # noqa: E402
from knowledge_engine.errors import WeKnoraUnavailableError  # noqa: E402


FIXTURE_TOKEN = "fixture-native-client-token-123456789"


class FixtureHandler(BaseHTTPRequestHandler):
    server: "FixtureServer"

    def do_GET(self) -> None:
        self.server.increment(self.path)
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        if self.path == "/api/v1/mcp-services":
            self._json(
                200,
                {
                    "success": True,
                    "data": [
                        {
                            "id": "fixture-mcp",
                            "name": "fixture service",
                            "type": "stdio",
                            "enabled": True,
                            "tools_count": 2,
                            "resources_count": 1,
                        }
                    ],
                },
            )
            return
        if self.path == "/api/v1/vector-stores/types":
            self._json(
                200,
                {
                    "success": True,
                    "data": [
                        {
                            "type": "postgres",
                            "name": "PostgreSQL",
                            "description": "fixture vector store type",
                            "fields": [{"name": "password", "configured": True}],
                        }
                    ],
                },
            )
            return
        if self.path == "/auth-error":
            self._json(
                401,
                {
                    "message": (
                        "Authorization: Bearer "
                        f"{FIXTURE_TOKEN}; token={FIXTURE_TOKEN}"
                    )
                },
            )
            return
        self._json(404, {"message": "missing"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status_code: int, payload: dict[str, object]) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))


class FixtureServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), FixtureHandler)
        self.counts: defaultdict[str, int] = defaultdict(int)

    @property
    def base_url(self) -> str:
        host, port = self.server_address
        return f"http://{host}:{port}"

    def increment(self, path: str) -> int:
        self.counts[path] += 1
        return self.counts[path]


@contextmanager
def fixture_server() -> FixtureServer:
    server = FixtureServer()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> int:
    results: list[str] = []
    with fixture_server() as server:
        backend = WeKnoraApiBackend(
            base_url=server.base_url,
            service_token=FIXTURE_TOKEN,
            timeout=1,
            workspace_id="fixture-workspace",
            default_kb_id="fixture-kb",
            retry_attempts=0,
            retry_backoff_seconds=0,
        )
        _assert(isinstance(backend.client, WeKnoraNativeClient), "shared client object is attached", results)

        operations = _count_client_calls(backend)
        health = backend.health()
        mcp_services = backend.list_mcp_services()
        vector_types = backend.list_vector_store_types()

        _assert(health.get("status") == "ok", "health path uses client", results)
        _assert(len(mcp_services) == 1, "MCP service path uses client", results)
        _assert(len(vector_types) == 1, "vector store type path uses client", results)
        _assert(
            operations == [
                ("GET", "/health"),
                ("GET", "/api/v1/mcp-services"),
                ("GET", "/api/v1/vector-stores/types"),
            ],
            "existing native methods share one request_json contract",
            results,
        )

        status = backend.native_client_status()
        serialized_status = json.dumps(status, sort_keys=True)
        _assert(status.get("schema_version") == "wnx-p0-01", "client status schema is explicit", results)
        _assert(status.get("trace_id_supported") is True, "trace metadata is declared", results)
        _assert(FIXTURE_TOKEN not in serialized_status, "client status hides service token", results)
        _assert(server.base_url not in serialized_status, "client status hides base URL value", results)

        _expect_sanitized_error(backend, results)

    print(
        json.dumps(
            {
                "decision": "PASS",
                "evidence_type": "fixture_contract_redaction",
                "client": "WeKnoraNativeClient",
                "shared_paths": [
                    "/health",
                    "/api/v1/mcp-services",
                    "/api/v1/vector-stores/types",
                ],
                "checks": results,
            },
            indent=2,
        )
    )
    return 0


def _count_client_calls(backend: WeKnoraApiBackend) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    original = backend.client.request_json

    def counted(method: str, path: str, payload: dict | None = None) -> dict | list:
        calls.append((method, path))
        return original(method, path, payload)

    backend.client.request_json = counted  # type: ignore[method-assign]
    return calls


def _expect_sanitized_error(backend: WeKnoraApiBackend, results: list[str]) -> None:
    try:
        backend._request_json("GET", "/auth-error")
    except WeKnoraUnavailableError as exc:
        message = str(exc)
        public = exc.to_public_dict()
        serialized_public = json.dumps(public, sort_keys=True)
        _assert(FIXTURE_TOKEN not in message, "error message hides service token", results)
        _assert(FIXTURE_TOKEN not in serialized_public, "public error hides service token", results)
        _assert("[redacted]" in message, "error message includes redaction marker", results)
        _assert(public.get("error_code") == "weknora_http_401", "public error code is stable", results)
        _assert(public.get("retryable") is False, "auth error retry flag is stable", results)
        return
    raise AssertionError("expected sanitized WeKnoraUnavailableError")


def _assert(condition: bool, message: str, results: list[str]) -> None:
    if not condition:
        raise AssertionError(message)
    results.append(message)


if __name__ == "__main__":
    raise SystemExit(main())
