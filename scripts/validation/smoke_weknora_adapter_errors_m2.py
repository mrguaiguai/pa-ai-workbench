"""Fixture smoke for P3-M2-A1 WeKnora adapter error mapping.

This script never calls live WeKnora and never reads .env. It starts a local
HTTP fixture server plus monkeypatches network failures to prove that stable
typed errors, retryable flags, conservative retries, and secret redaction work.
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
from urllib.error import URLError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from knowledge_engine.backends import weknora_api_backend as adapter_module  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import WeKnoraAuthError  # noqa: E402
from knowledge_engine.errors import WeKnoraNetworkError  # noqa: E402
from knowledge_engine.errors import WeKnoraNotFoundError  # noqa: E402
from knowledge_engine.errors import WeKnoraRateLimitError  # noqa: E402
from knowledge_engine.errors import WeKnoraResponseMappingError  # noqa: E402
from knowledge_engine.errors import WeKnoraServerError  # noqa: E402
from knowledge_engine.errors import WeKnoraTimeoutError  # noqa: E402
from knowledge_engine.errors import WeKnoraUnavailableError  # noqa: E402


FIXTURE_TOKEN = "fixture-secret-token-123456789"


class FixtureHandler(BaseHTTPRequestHandler):
    server: "FixtureServer"

    def do_GET(self) -> None:
        count = self.server.increment(self.path)
        if self.path == "/auth-error":
            self._json(
                401,
                {
                    "error": {
                        "code": "AUTH_FAILED",
                        "message": (
                            "Authorization: Bearer "
                            f"{FIXTURE_TOKEN} token={FIXTURE_TOKEN}"
                        ),
                    }
                },
            )
            return
        if self.path == "/forbidden":
            self._json(403, {"message": "forbidden"})
            return
        if self.path == "/missing":
            self._json(404, {"message": "missing resource"})
            return
        if self.path == "/rate-limit":
            self._json(429, {"error_code": "RATE_LIMIT", "message": "too many"})
            return
        if self.path == "/server-flaky":
            if count == 1:
                self._json(503, {"message": "temporary outage"})
                return
            self._json(200, {"ok": True})
            return
        if self.path == "/server-stable":
            self._json(503, {"message": "still unavailable"})
            return
        if self.path == "/invalid-json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{not-json")
            return
        self._json(200, {"ok": True})

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


@contextmanager
def patched_urlopen(func: Callable[..., object]):
    original = adapter_module.urlopen
    adapter_module.urlopen = func
    try:
        yield
    finally:
        adapter_module.urlopen = original


def main() -> int:
    results: list[str] = []
    with fixture_server() as server:
        backend = WeKnoraApiBackend(
            base_url=server.base_url,
            service_token=FIXTURE_TOKEN,
            timeout=1,
            retry_attempts=1,
            retry_backoff_seconds=0,
        )

        _expect_error(
            "401 maps to auth error",
            lambda: backend._request_json("GET", "/auth-error"),
            WeKnoraAuthError,
            retryable=False,
            status_code=401,
            results=results,
        )
        _expect_count(server, "/auth-error", 1, results)
        _expect_no_token_leak(
            lambda: backend._request_json("GET", "/auth-error"),
            results,
        )

        _expect_error(
            "403 maps to auth error",
            lambda: backend._request_json("GET", "/forbidden"),
            WeKnoraAuthError,
            retryable=False,
            status_code=403,
            results=results,
        )
        _expect_count(server, "/forbidden", 1, results)

        _expect_error(
            "404 maps to not found error",
            lambda: backend._request_json("GET", "/missing"),
            WeKnoraNotFoundError,
            retryable=False,
            status_code=404,
            results=results,
        )
        _expect_count(server, "/missing", 1, results)

        _expect_error(
            "429 maps to rate limit error and retries",
            lambda: backend._request_json("GET", "/rate-limit"),
            WeKnoraRateLimitError,
            retryable=True,
            status_code=429,
            results=results,
        )
        _expect_count(server, "/rate-limit", 2, results)

        value = backend._request_json("GET", "/server-flaky")
        _assert(value == {"ok": True}, "5xx retry can recover", results)
        _expect_count(server, "/server-flaky", 2, results)

        _expect_error(
            "5xx maps to server error",
            lambda: backend._request_json("GET", "/server-stable"),
            WeKnoraServerError,
            retryable=True,
            status_code=503,
            results=results,
        )
        _expect_count(server, "/server-stable", 2, results)

        _expect_error(
            "invalid JSON maps to response mapping error without retry",
            lambda: backend._request_json("GET", "/invalid-json"),
            WeKnoraResponseMappingError,
            retryable=False,
            status_code=None,
            results=results,
        )
        _expect_count(server, "/invalid-json", 1, results)

    _expect_monkeypatched_errors(results)

    print(json.dumps({"decision": "PASS", "checks": results}, indent=2))
    return 0


def _expect_error(
    name: str,
    action: Callable[[], object],
    expected_type: type[WeKnoraUnavailableError],
    *,
    retryable: bool,
    status_code: int | None,
    results: list[str],
) -> WeKnoraUnavailableError:
    try:
        action()
    except expected_type as exc:
        _assert(exc.retryable is retryable, f"{name}: retryable flag", results)
        _assert(exc.status_code == status_code, f"{name}: status code", results)
        _assert(exc.error_code, f"{name}: error code present", results)
        _assert(FIXTURE_TOKEN not in str(exc), f"{name}: token redacted", results)
        results.append(name)
        return exc
    raise AssertionError(f"{name}: expected {expected_type.__name__}")


def _expect_no_token_leak(action: Callable[[], object], results: list[str]) -> None:
    try:
        action()
    except WeKnoraUnavailableError as exc:
        message = str(exc)
        _assert(FIXTURE_TOKEN not in message, "secret token is not logged", results)
        _assert("[redacted]" in message, "sensitive marker is redacted", results)
        results.append("error message redaction")
        return
    raise AssertionError("expected WeKnoraUnavailableError")


def _expect_count(
    server: FixtureServer,
    path: str,
    expected_count: int,
    results: list[str],
) -> None:
    actual = server.counts[path]
    _assert(
        actual == expected_count,
        f"{path} request count expected {expected_count}, got {actual}",
        results,
    )
    results.append(f"{path} request count={actual}")


def _expect_monkeypatched_errors(results: list[str]) -> None:
    timeout_backend = WeKnoraApiBackend(
        base_url="http://127.0.0.1:1",
        service_token=FIXTURE_TOKEN,
        timeout=1,
        retry_attempts=1,
        retry_backoff_seconds=0,
    )
    calls = {"timeout": 0, "network": 0}

    def timeout_urlopen(*args: object, **kwargs: object) -> object:
        calls["timeout"] += 1
        raise TimeoutError("timed out")

    with patched_urlopen(timeout_urlopen):
        _expect_error(
            "timeout maps to timeout error and retries",
            lambda: timeout_backend._request_json("GET", "/timeout"),
            WeKnoraTimeoutError,
            retryable=True,
            status_code=None,
            results=results,
        )
    _assert(calls["timeout"] == 2, "timeout retried once", results)
    results.append("timeout request count=2")

    def network_urlopen(*args: object, **kwargs: object) -> object:
        calls["network"] += 1
        raise URLError("connection refused")

    with patched_urlopen(network_urlopen):
        _expect_error(
            "network error maps to network error and retries",
            lambda: timeout_backend._request_json("GET", "/network"),
            WeKnoraNetworkError,
            retryable=True,
            status_code=None,
            results=results,
        )
    _assert(calls["network"] == 2, "network error retried once", results)
    results.append("network request count=2")


def _assert(condition: bool, message: str, results: list[str]) -> None:
    if not condition:
        print(json.dumps({"decision": "FAIL", "reason": message}, indent=2), file=sys.stderr)
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
