"""Check WNX internal deployment readiness without exposing runtime secrets.

Default mode validates recovery scripts and runbook structure. With
``--start-services`` it starts temporary PA backend and frontend processes on
free localhost ports, checks live status endpoints, and terminates both
processes before exiting.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
DOCS_ROOT = PROJECT_ROOT / "docs"

RUNBOOK_PATH = DOCS_ROOT / "WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md"

DEFAULT_NODE_BIN = Path(
    "/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
)

REQUIRED_FILES = (
    "scripts/pa-dev-services.sh",
    "scripts/install-pa-launchagents.sh",
    "scripts/uninstall-pa-launchagents.sh",
    "backend/app/api/health.py",
    "backend/app/api/model.py",
    "backend/app/api/native_status.py",
    "backend/scripts/check_weknora_native_expansion_acceptance.py",
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/node_modules/vite/bin/vite.js",
)

RUNBOOK_MARKERS = (
    "WNX-P0-05",
    "scripts/pa-dev-services.sh start",
    "scripts/pa-dev-services.sh stop",
    "scripts/pa-dev-services.sh restart",
    "scripts/install-pa-launchagents.sh",
    "scripts/uninstall-pa-launchagents.sh",
    "/health",
    "/api/status",
    "/api/model/status",
    "/api/native/status",
    "WeKnora",
    "model",
    "embedding",
    "vector store",
    "parser",
    "LaunchAgents",
    "do not commit",
)

SECRET_PATTERNS = {
    "secret_bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    "secret_openai_key": re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{14,}\b"),
    "secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|service[_-]?token|password|secret|private[_-]?key|authorization)"
        r"\s*[:=]\s*(?!\[?redacted\]?|omitted|configured\b|true\b|false\b)"
        r"[^\s`|,;]{8,}"
    ),
    "private_key_block": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
}


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


class ReadinessError(RuntimeError):
    """Raised when a readiness gate fails."""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    gates = _run_static_gates()
    if args.start_services:
        gates.extend(_run_live_service_gates())

    decision = "PASS" if all(gate.status == "PASS" for gate in gates) else "FAIL"
    print("WeKnora native deployment readiness")
    print(f"- decision: {decision}")
    print(f"- mode: {'live-services' if args.start_services else 'static'}")
    for gate in gates:
        print(f"- {gate.name}: {gate.status} - {gate.detail}")
    return 0 if decision == "PASS" else 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check WNX deployment readiness.")
    parser.add_argument(
        "--start-services",
        action="store_true",
        help="start temporary backend/frontend and validate live status endpoints",
    )
    return parser.parse_args(argv)


def _run_static_gates() -> list[Gate]:
    return [
        _check_required_files(),
        _check_service_scripts(),
        _check_frontend_scripts(),
        _check_runbook(),
    ]


def _check_required_files() -> Gate:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    if missing:
        return Gate("required deployment artifacts", "FAIL", "missing " + ", ".join(missing))
    return Gate("required deployment artifacts", "PASS", f"{len(REQUIRED_FILES)} files present")


def _check_service_scripts() -> Gate:
    dev = _read(PROJECT_ROOT / "scripts" / "pa-dev-services.sh")
    install = _read(PROJECT_ROOT / "scripts" / "install-pa-launchagents.sh")
    uninstall = _read(PROJECT_ROOT / "scripts" / "uninstall-pa-launchagents.sh")
    required = (
        "start_backend",
        "start_frontend",
        "stop_one",
        "restart",
        "status",
        "logs",
        "com.pa-ai-workbench.backend",
        "com.pa-ai-workbench.frontend",
        "KeepAlive",
        "launchctl bootstrap",
        "launchctl bootout",
    )
    combined = "\n".join([dev, install, uninstall])
    missing = [marker for marker in required if marker not in combined]
    if missing:
        return Gate("service recovery scripts", "FAIL", "missing " + ", ".join(missing))
    if _contains_secret_shape(combined):
        return Gate("service recovery scripts", "FAIL", "secret-shaped text found")
    return Gate("service recovery scripts", "PASS", "manual and LaunchAgent recovery paths present")


def _check_frontend_scripts() -> Gate:
    package_json = _read(FRONTEND_ROOT / "package.json")
    if '"build"' not in package_json or '"dev"' not in package_json:
        return Gate("frontend recovery entrypoints", "FAIL", "frontend dev/build scripts missing")
    node_bin = _node_bin()
    if not node_bin:
        return Gate("frontend recovery entrypoints", "FAIL", "node executable not found")
    return Gate("frontend recovery entrypoints", "PASS", "node, Vite dev, and build entrypoints present")


def _check_runbook() -> Gate:
    if not RUNBOOK_PATH.exists():
        return Gate("deployment readiness runbook", "FAIL", "runbook missing")
    text = _read(RUNBOOK_PATH)
    missing = [marker for marker in RUNBOOK_MARKERS if marker not in text]
    if missing:
        return Gate("deployment readiness runbook", "FAIL", "missing " + ", ".join(missing))
    if _contains_secret_shape(text):
        return Gate("deployment readiness runbook", "FAIL", "secret-shaped text found")
    return Gate("deployment readiness runbook", "PASS", "operator commands and status checks documented")


def _run_live_service_gates() -> list[Gate]:
    backend_port = _free_port()
    frontend_port = _free_port()
    backend = _start_backend(backend_port, frontend_port)
    frontend = None
    gates: list[Gate] = []
    try:
        _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
        frontend = _start_frontend(frontend_port, backend_port)
        gates.append(_check_health(backend_port))
        gates.append(_check_api_status(backend_port))
        gates.append(_check_model_status(backend_port))
        gates.append(_check_native_status(backend_port))
        gates.append(_check_frontend_html(frontend_port))
    finally:
        _terminate(frontend)
        _terminate(backend)
    return gates


def _start_backend(port: int, frontend_port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["CORS_ORIGINS"] = (
        f"http://127.0.0.1:{frontend_port},http://localhost:{frontend_port},"
        "http://127.0.0.1:5173,http://localhost:5173"
    )
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
        cwd=str(BACKEND_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _start_frontend(frontend_port: int, backend_port: int) -> subprocess.Popen[str]:
    node_bin = _node_bin()
    if not node_bin:
        raise ReadinessError("node executable not found")
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = f"http://127.0.0.1:{backend_port}"
    process = subprocess.Popen(
        [
            node_bin,
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            str(frontend_port),
            "--strictPort",
        ],
        cwd=str(FRONTEND_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _wait_for_text(f"http://127.0.0.1:{frontend_port}/index.html", process)
    return process


def _check_health(port: int) -> Gate:
    data = _wait_for_json(f"http://127.0.0.1:{port}/health")
    if data.get("status") != "ok" or data.get("service") != "pa-ai-workbench-backend":
        return Gate("/health", "FAIL", "unexpected health payload")
    return Gate("/health", "PASS", "backend health ok")


def _check_api_status(port: int) -> Gate:
    data = _wait_for_json(f"http://127.0.0.1:{port}/api/status")
    if data.get("status") != "ok":
        return Gate("/api/status", "FAIL", "status is not ok")
    if data.get("knowledge_backend") != "weknora_api":
        return Gate("/api/status", "FAIL", "knowledge backend is not weknora_api")
    if data.get("mock_mode") is not False:
        return Gate("/api/status", "FAIL", "mock mode is not false")
    weknora = data.get("weknora") or {}
    if not isinstance(weknora, dict) or not weknora.get("connected"):
        return Gate("/api/status", "FAIL", "WeKnora is not connected")
    mapping = weknora.get("kb_mapping") or {}
    mapping_status = mapping.get("status") if isinstance(mapping, dict) else None
    return Gate(
        "/api/status",
        "PASS",
        f"weknora connected; kb_mapping={mapping_status or 'unknown'}",
    )


def _check_model_status(port: int) -> Gate:
    data = _wait_for_json(f"http://127.0.0.1:{port}/api/model/status")
    chat = data.get("chat") or {}
    embedding = data.get("embedding") or {}
    if data.get("mock_mode") is not False:
        return Gate("/api/model/status", "FAIL", "model status reports mock mode")
    if not data.get("configured"):
        return Gate("/api/model/status", "FAIL", "model status is not configured")
    if not chat.get("configured") or chat.get("mock"):
        return Gate("/api/model/status", "FAIL", "chat model is not live-configured")
    if not embedding.get("configured") or embedding.get("mock"):
        return Gate("/api/model/status", "FAIL", "embedding is not live-configured")
    return Gate(
        "/api/model/status",
        "PASS",
        f"chat={chat.get('provider')}; embedding={embedding.get('provider')}",
    )


def _check_native_status(port: int) -> Gate:
    data = _wait_for_json(f"http://127.0.0.1:{port}/api/native/status?limit=5")
    groups = data.get("groups") or {}
    if data.get("masked") is not True or data.get("evidence_type") != "live_api":
        return Gate("/api/native/status", "FAIL", "native status is not masked live_api")
    if int(data.get("group_count") or 0) != 15:
        return Gate("/api/native/status", "FAIL", "native status group_count is not 15")
    required_live = {
        "system_health_status_deployment",
        "workspace_knowledge_base",
        "mcp",
        "web_search",
        "vector_store",
        "model_embedding_rerank_parser",
    }
    not_live = [
        group_id
        for group_id in sorted(required_live)
        if not isinstance(groups.get(group_id), dict) or groups[group_id].get("status") != "live"
    ]
    if not_live:
        return Gate("/api/native/status", "FAIL", "not live: " + ", ".join(not_live))
    forbidden = _forbidden_json_paths(data)
    if forbidden:
        return Gate("/api/native/status", "FAIL", "forbidden fields: " + ", ".join(forbidden[:5]))
    return Gate(
        "/api/native/status",
        "PASS",
        "15 masked groups; vector/model/parser group live; backlog remains visible",
    )


def _check_frontend_html(port: int) -> Gate:
    text = _wait_for_text(f"http://127.0.0.1:{port}/index.html")
    if "PA 智能工作台" not in text:
        return Gate("frontend service", "FAIL", "frontend HTML title missing")
    return Gate("frontend service", "PASS", "Vite frontend responded with PA shell HTML")


def _wait_for_json(url: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=3) as response:
                if response.status == 200:
                    parsed = json.loads(response.read().decode("utf-8"))
                    if isinstance(parsed, dict):
                        return parsed
        except Exception as exc:  # noqa: BLE001
            last_error = _safe_reason(exc)
        time.sleep(0.25)
    raise ReadinessError(f"{url} did not return JSON: {last_error}")


def _wait_for_text(url: str, process: subprocess.Popen[str] | None = None) -> str:
    deadline = time.monotonic() + 30
    last_error = ""
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise ReadinessError("temporary frontend exited early: " + _safe_reason(RuntimeError(stderr)))
        try:
            with urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return response.read().decode("utf-8", errors="replace")
        except (TimeoutError, URLError, OSError) as exc:
            last_error = _safe_reason(exc)
        time.sleep(0.25)
    raise ReadinessError(f"{url} did not respond: {last_error}")


def _terminate(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _node_bin() -> str | None:
    if DEFAULT_NODE_BIN.exists() and os.access(DEFAULT_NODE_BIN, os.X_OK):
        return str(DEFAULT_NODE_BIN)
    return shutil.which("node")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReadinessError(f"missing file: {path.relative_to(PROJECT_ROOT)}") from exc


def _contains_secret_shape(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS.values())


def _forbidden_json_paths(value: object, prefix: str = "$") -> list[str]:
    forbidden_names = {
        "api_key",
        "token",
        "password",
        "secret",
        "headers",
        "auth_config",
        "base_url",
        "url",
        "connection_config",
        "provider_payload",
        "raw",
        "records",
        "vectors",
        "chunks",
        "logs",
        "database_url",
    }
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if key in forbidden_names:
                paths.append(path)
            paths.extend(_forbidden_json_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_forbidden_json_paths(item, f"{prefix}[{index}]"))
    elif isinstance(value, str) and re.search(r"https?://|sk-[A-Za-z0-9]|Bearer\s+|BEGIN .*PRIVATE KEY", value):
        paths.append(prefix)
    return paths


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password", "token"):
        text = text.replace(marker, "[redacted]")
    return text[:240]


if __name__ == "__main__":
    raise SystemExit(main())
