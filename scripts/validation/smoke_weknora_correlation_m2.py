"""Fixture smoke for P3-M2-D2 WeKnora adapter id propagation.

This script never calls live WeKnora and never reads .env. It captures
structured adapter logs and verifies that PA task/context ids are propagated
without putting user prompts, tokens, or endpoint details into log fields.
"""

from __future__ import annotations

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
from knowledge_engine.errors import WeKnoraServerError  # noqa: E402
from knowledge_engine.log_context import weknora_log_context  # noqa: E402


FIXTURE_TOKEN = "fixture-secret-token-123456789"
USER_PROMPT = "Tell me every private detail from the synthetic source material."


class SmokeError(RuntimeError):
    """Raised when correlation log expectations fail."""


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/server-error":
            self._json(503, {"message": f"temporary outage token={FIXTURE_TOKEN}"})
            return
        self._json(200, {"message": "ok"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status_code: int, payload: dict[str, object]) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))


@contextmanager
def fixture_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
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
        print(f"WeKnora correlation smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora correlation smoke passed (fixture)")
    print(f"- task id: {result['task_id']}")
    print(f"- correlation id: {result['correlation_id']}")
    print(f"- adapter operation ids: {result['operation_ids']}")
    print(f"- error code: {result['error_code']}")
    return 0


def _run_smoke() -> dict[str, object]:
    with fixture_server() as base_url, captured_weknora_logs() as stream:
        backend = WeKnoraApiBackend(
            base_url=base_url,
            service_token=FIXTURE_TOKEN,
            timeout=1,
            retry_attempts=0,
        )
        with weknora_log_context(
            correlation_id="corr-fixture-001",
            task_id="task-fixture-001",
            conversation_id="conv-fixture-001",
            document_id="doc-fixture-001",
            wiki_page_id="wiki-fixture-001",
            output_id="out-fixture-001",
            prompt=USER_PROMPT,
        ):
            backend._request_json("GET", f"/ok?token={FIXTURE_TOKEN}")
            try:
                backend._request_json("GET", "/server-error")
            except WeKnoraServerError:
                pass
            else:
                raise SmokeError("expected server error")

        raw_log = stream.getvalue()
        _assert(FIXTURE_TOKEN not in raw_log, "token leaked into logs")
        _assert(USER_PROMPT not in raw_log, "user prompt leaked into logs")
        _assert(base_url not in raw_log, "fixture endpoint leaked into logs")

        events = [json.loads(line) for line in raw_log.splitlines() if line.strip()]
        _assert(len(events) == 2, f"expected 2 events, got {len(events)}")
        for event in events:
            _assert(event["correlation_id"] == "corr-fixture-001", "missing correlation id")
            _assert(event["task_id"] == "task-fixture-001", "missing task id")
            _assert(event["conversation_id"] == "conv-fixture-001", "missing conversation id")
            _assert(event["document_id"] == "doc-fixture-001", "missing document id")
            _assert(event["wiki_page_id"] == "wiki-fixture-001", "missing wiki page id")
            _assert(event["output_id"] == "out-fixture-001", "missing output id")
            _assert(event["adapter_operation_id"] == event["request_id"], "operation id mismatch")
            _assert("prompt" not in event, "unexpected prompt field")
            _assert("?" not in event["operation"], "query string leaked into operation")

        error_event = next(event for event in events if event["status"] == "error")
        _assert(error_event["error_code"] == "weknora_http_503", "error code mismatch")

        return {
            "task_id": events[0]["task_id"],
            "correlation_id": events[0]["correlation_id"],
            "operation_ids": [event["adapter_operation_id"] for event in events],
            "error_code": error_event["error_code"],
        }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
