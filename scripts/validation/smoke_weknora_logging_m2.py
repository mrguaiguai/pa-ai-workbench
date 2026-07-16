"""Fixture smoke for P3-M2-D1 WeKnora adapter logging redaction.

This script never calls live WeKnora and never reads .env. It starts a local
fixture server, captures the adapter logger, and verifies that structured
metadata is useful for troubleshooting without leaking tokens, private
endpoints, full prompts, raw responses, or long document/chunk text.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
import io
import json
import logging
from pathlib import Path
import sys
from threading import Thread


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from knowledge_engine.backends.weknora_api_backend import WEKNORA_LOGGER  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WEKNORA_LOG_EXCERPT_LIMIT  # noqa: E402
from knowledge_engine.errors import WeKnoraAuthError  # noqa: E402
from knowledge_engine.errors import WeKnoraResponseMappingError  # noqa: E402


FIXTURE_TOKEN = "fixture-secret-token-123456789"
PRIVATE_ENDPOINT = "http://weknora.internal.example/private/api"
LONG_TEXT = "Synthetic confidential chunk text. " * 30


class SmokeError(RuntimeError):
    """Raised when logging expectations fail."""


class FixtureHandler(BaseHTTPRequestHandler):
    server: "FixtureServer"

    def do_GET(self) -> None:
        count = self.server.increment(self.path)
        if self.path.startswith("/ok"):
            self._json(
                200,
                {
                    "message": (
                        f"Authorization: Bearer {FIXTURE_TOKEN}; "
                        f"endpoint={PRIVATE_ENDPOINT}; {LONG_TEXT}"
                    ),
                    "status": "ok",
                },
            )
            return
        if self.path == "/auth":
            self._json(
                401,
                {
                    "message": (
                        f"token={FIXTURE_TOKEN}; endpoint={PRIVATE_ENDPOINT}; "
                        "authentication failed"
                    )
                },
            )
            return
        if self.path == "/flaky":
            if count == 1:
                self._json(503, {"message": "temporary fixture outage"})
                return
            self._json(200, {"message": "recovered"})
            return
        if self.path == "/invalid-json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{not-json")
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


@contextmanager
def captured_weknora_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    original_level = WEKNORA_LOGGER.level
    original_propagate = WEKNORA_LOGGER.propagate
    WEKNORA_LOGGER.setLevel(logging.INFO)
    WEKNORA_LOGGER.propagate = False
    WEKNORA_LOGGER.addHandler(handler)
    try:
        yield stream
    finally:
        WEKNORA_LOGGER.removeHandler(handler)
        WEKNORA_LOGGER.setLevel(original_level)
        WEKNORA_LOGGER.propagate = original_propagate


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora logging smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora logging smoke passed (fixture)")
    print(f"- log events: {result['events']}")
    print(f"- retry count: {result['retry_count']}")
    print(f"- error codes: {', '.join(result['error_codes'])}")
    print(f"- max excerpt chars: {result['max_excerpt_chars']}")
    return 0


def _run_smoke() -> dict[str, object]:
    with fixture_server() as server, captured_weknora_logs() as stream:
        backend = WeKnoraApiBackend(
            base_url=server.base_url,
            service_token=FIXTURE_TOKEN,
            timeout=1,
            retry_attempts=1,
            retry_backoff_seconds=0,
        )

        backend._request_json("GET", f"/ok?token={FIXTURE_TOKEN}")
        backend._request_json("GET", "/flaky")
        _expect_error(lambda: backend._request_json("GET", "/auth"), WeKnoraAuthError)
        _expect_error(
            lambda: backend._request_json("GET", "/invalid-json"),
            WeKnoraResponseMappingError,
        )

        raw_log = stream.getvalue()
        _assert(FIXTURE_TOKEN not in raw_log, "token leaked into logs")
        _assert(PRIVATE_ENDPOINT not in raw_log, "private endpoint leaked into logs")
        _assert("raw_response" not in raw_log, "raw response marker leaked into logs")
        _assert(LONG_TEXT[:120] not in raw_log, "long text leaked into logs")

        events = [json.loads(line) for line in raw_log.splitlines() if line.strip()]
        _assert(len(events) == 4, f"expected 4 log events, got {len(events)}")
        _assert(all(event["event"] == "weknora_adapter_call" for event in events), "event mismatch")
        _assert(all(event["source"] == "weknora_api" for event in events), "source mismatch")
        _assert(all(event.get("request_id") for event in events), "missing request id")
        _assert(all("http://" not in event["operation"] for event in events), "operation leaked endpoint")
        _assert(all("?" not in event["operation"] for event in events), "operation leaked query string")
        _assert(all("duration_ms" in event for event in events), "missing duration")
        _assert(all("retry_count" in event for event in events), "missing retry count")
        _assert(all(len(event.get("excerpt", "")) <= WEKNORA_LOG_EXCERPT_LIMIT for event in events), "excerpt too long")

        ok_event = _find_event(events, "GET /ok")
        flaky_event = _find_event(events, "GET /flaky")
        auth_event = _find_event(events, "GET /auth")
        invalid_event = _find_event(events, "GET /invalid-json")

        _assert(ok_event["status"] == "ok", "ok status mismatch")
        _assert(ok_event["status_code"] == 200, "ok status code mismatch")
        _assert(flaky_event["retry_count"] == 1, "retry count mismatch")
        _assert(flaky_event["status"] == "ok", "flaky status mismatch")
        _assert(auth_event["status"] == "error", "auth status mismatch")
        _assert(auth_event["error_code"] == "weknora_http_401", "auth error code mismatch")
        _assert(invalid_event["status"] == "error", "invalid-json status mismatch")
        _assert(invalid_event["error_code"] == "weknora_invalid_json", "invalid-json error mismatch")

        return {
            "events": len(events),
            "retry_count": flaky_event["retry_count"],
            "error_codes": [
                auth_event["error_code"],
                invalid_event["error_code"],
            ],
            "max_excerpt_chars": max(len(event.get("excerpt", "")) for event in events),
        }


def _expect_error(func, expected_type: type[Exception]) -> None:
    try:
        func()
    except expected_type:
        return
    raise SmokeError(f"expected {expected_type.__name__}")


def _find_event(events: list[dict[str, object]], operation: str) -> dict[str, object]:
    for event in events:
        if event.get("operation") == operation:
            return event
    raise SmokeError(f"missing log event for {operation}")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
