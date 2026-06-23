"""Live WNX-P1-01 knowledge-base management smoke.

The script starts a temporary PA backend, calls the PA BFF knowledge-base
management endpoints, and verifies that list/read/active-selection work through
real WeKnora while mutation-heavy operations remain explicit backlog. It prints
only statuses and counts, never KB ids, service tokens, or raw upstream payloads.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import struct
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
DEFAULT_NODE_BIN = Path(
    "/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
)
CHROME_BIN = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-kb-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'kb-smoke.db'}"
        backend = _start_backend(backend_port, database_url)
        frontend = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/knowledge-bases/native/overview?limit=10")

            _assert(overview.get("schema_version") == "wnx-p1-01", "schema version is wnx-p1-01")
            _assert(overview.get("evidence_type") == "live_api", "evidence type is live_api")
            _assert(overview.get("status") == "live", "overview status is live")
            _assert(int(overview.get("total") or 0) > 0, "knowledge base list is non-empty")
            _assert(bool(overview.get("masked")), "overview is masked")

            active = overview.get("active_selection") if isinstance(overview.get("active_selection"), dict) else {}
            items = overview.get("items") if isinstance(overview.get("items"), list) else []
            selected_id = str(active.get("kb_id") or (items[0].get("id") if items and isinstance(items[0], dict) else ""))
            _assert(bool(selected_id), "active or first KB id is available internally")

            selected = _request_json(
                backend_port,
                "POST",
                "/api/knowledge-bases/native/active",
                {"kb_id": selected_id},
            )
            selected_active = (
                selected.get("active_selection")
                if isinstance(selected.get("active_selection"), dict)
                else {}
            )
            _assert(selected.get("status") == "live", "active selection POST is live")
            _assert(bool(selected_active.get("snapshot_saved")), "PA selection snapshot is saved")
            _assert(isinstance(selected.get("mutation_backlog"), list), "mutation backlog is explicit")

            refreshed = _request_json(backend_port, "GET", "/api/knowledge-bases/native/overview?limit=10")
            refreshed_active = (
                refreshed.get("active_selection")
                if isinstance(refreshed.get("active_selection"), dict)
                else {}
            )
            _assert(bool(refreshed_active.get("snapshot_saved")), "overview reads PA active snapshot")

            surfaces = refreshed.get("surfaces") if isinstance(refreshed.get("surfaces"), dict) else {}
            tags = surfaces.get("tags") if isinstance(surfaces.get("tags"), dict) else {}
            mutations = surfaces.get("mutations") if isinstance(surfaces.get("mutations"), dict) else {}
            _assert(tags.get("status") == "live", "tag list surface is live")
            _assert(mutations.get("status") == "backlog", "unsafe mutation surface is backlog")

            print("WeKnora native KB management")
            print("- decision: PASS")
            print("- evidence_type: live_api")
            print(f"- api: list_total={int(refreshed.get('total') or 0)} active_snapshot=saved")
            print(f"- tags: status={tags.get('status')} count={int(tags.get('count') or 0)}")
            print("- mutations: create/update/delete/pin/tag write flows remain backlog")
            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_library_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in ("资料库", "活动知识库", "上传目标"):
                    _assert(marker in dom, f"browser DOM contains {marker}")
                _assert(
                    "当前活动" in dom or "设为活动" in dom,
                    "browser DOM contains active selection action state",
                )
                print("- browser: Library DOM rendered KB selector")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _start_backend(port: int, database_url: str) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["CORS_ORIGINS"] = "http://127.0.0.1:5173,http://localhost:5173"
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _start_frontend(port: int, backend_port: int) -> subprocess.Popen[str]:
    node_bin = _node_bin()
    if node_bin is None:
        raise RuntimeError("node executable not found for frontend browser smoke")
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = f"http://127.0.0.1:{backend_port}"
    return subprocess.Popen(
        [
            str(node_bin),
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--strictPort",
        ],
        cwd=FRONTEND_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _request_json(port: int, method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{method} {path} returned non-object JSON")
    return data


def _wait_for_json(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                json.loads(response.read().decode("utf-8"))
                return
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.3)
    raise RuntimeError(f"backend did not become ready: {last_error}")


def _wait_for_html(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                text = response.read().decode("utf-8", errors="replace")
                if "<div id=\"root\">" in text:
                    return
        except (URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(0.3)
    raise RuntimeError(f"frontend did not become ready: {last_error}")


def _dump_library_dom(port: int, user_data_dir: Path) -> str:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/library', safe=':/?=&')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        return _read_dom_text_via_cdp(ws_url)
    finally:
        _terminate(chrome)


def _wait_for_chrome(port: int, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            _request_chrome_json(port, "GET", "/json/version")
            return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Chrome DevTools endpoint did not become ready")


def _request_chrome_json(port: int, method: str, path: str) -> dict[str, Any]:
    request = Request(f"http://127.0.0.1:{port}{path}", method=method)
    with urlopen(request, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Chrome returned non-object JSON")
    return data


def _read_dom_text_via_cdp(ws_url: str) -> str:
    parsed = urlparse(ws_url)
    if parsed.hostname is None or parsed.port is None:
        raise RuntimeError("Chrome websocket URL is invalid")
    with socket.create_connection((parsed.hostname, parsed.port), timeout=10) as sock:
        _websocket_handshake(sock, parsed.path)
        seq = 0

        def send(method: str, params: dict[str, Any] | None = None) -> int:
            nonlocal seq
            seq += 1
            _websocket_send_json(sock, {"id": seq, "method": method, "params": params or {}})
            return seq

        send("Page.enable")
        send("Runtime.enable")
        time.sleep(5)
        eval_id = send(
            "Runtime.evaluate",
            {
                "expression": "document.body ? document.body.innerText : ''",
                "returnByValue": True,
            },
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            message = _websocket_recv_json(sock)
            if message.get("id") != eval_id:
                continue
            result = message.get("result")
            if not isinstance(result, dict):
                break
            value = result.get("result")
            if isinstance(value, dict):
                return str(value.get("value") or "")
        raise RuntimeError("Chrome CDP did not return DOM text")


def _websocket_handshake(sock: socket.socket, path: str) -> None:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        "Host: 127.0.0.1\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(request.encode("ascii"))
    response = sock.recv(4096).decode("latin1", errors="replace")
    accept = base64.b64encode(
        hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
    ).decode("ascii")
    if "101" not in response.split("\r\n", 1)[0] or accept not in response:
        raise RuntimeError("Chrome websocket handshake failed")


def _websocket_send_json(sock: socket.socket, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    mask = os.urandom(4)
    header = bytearray([0x81])
    length = len(data)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", length))
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
    sock.sendall(bytes(header) + mask + masked)


def _websocket_recv_json(sock: socket.socket) -> dict[str, Any]:
    first = _recv_exact(sock, 2)
    opcode = first[0] & 0x0F
    length = first[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(sock, 8))[0]
    masked = bool(first[1] & 0x80)
    mask = _recv_exact(sock, 4) if masked else b""
    data = _recv_exact(sock, length)
    if masked:
        data = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
    if opcode == 0x8:
        raise RuntimeError("Chrome websocket closed")
    return json.loads(data.decode("utf-8"))


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("websocket closed while reading")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _node_bin() -> Path | None:
    if DEFAULT_NODE_BIN.exists():
        return DEFAULT_NODE_BIN
    resolved = shutil.which("node")
    return Path(resolved) if resolved else None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _terminate(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
