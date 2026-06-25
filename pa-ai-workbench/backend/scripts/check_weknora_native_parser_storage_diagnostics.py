"""Live WNFC-P3-03 parser and storage diagnostics smoke.

This smoke proves parser/storage readiness through real WeKnora native
diagnostic APIs and one sanitized sample document parse. It prints only counts,
statuses, and bounded messages; it never prints service tokens, docreader
addresses, raw sample content, provider payloads, or storage credentials.
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
from urllib import error
from urllib.parse import quote
from urllib import request
from uuid import uuid4

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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTER_ROOT = PROJECT_ROOT.parent
DEFAULT_NATIVE_BASE_URL = "http://127.0.0.1:8080"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    env = _load_local_env()
    token = str(env.get("WEKNORA_SERVICE_TOKEN") or "").strip()
    native_base_url = str(env.get("WEKNORA_BASE_URL") or DEFAULT_NATIVE_BASE_URL).rstrip("/")

    print("WeKnora native parser/storage diagnostics")
    if not token:
        print("- decision: BLOCKED")
        print("- evidence_type: blocked evidence plus live api preflight")
        print("- blocker: WEKNORA_SERVICE_TOKEN is not configured")
        return 1

    parser_check = _check_parser_engines(native_base_url, token)
    storage_check = _check_local_storage(native_base_url, token)
    sample = _run_sample_parse(browser_mode=browser_mode)

    passed = (
        parser_check["engine_count"] > 0
        and parser_check["available_count"] > 0
        and storage_check["ok"]
        and sample["indexed"]
        and sample["chunk_count"] > 0
    )
    print(f"- decision: {'PASS' if passed else 'BLOCKED'}")
    print(
        "- evidence_type: "
        + ("live api/browser" if browser_mode and passed else "live api" if passed else "blocked evidence plus live api")
    )
    print(
        "- parser_check: engines={engines} available={available} connected={connected}".format(
            engines=parser_check["engine_count"],
            available=parser_check["available_count"],
            connected=str(parser_check["connected"]).lower(),
        )
    )
    print(
        "- storage_check: provider=local ok={ok} message={message}".format(
            ok=str(storage_check["ok"]).lower(),
            message=_safe_message(storage_check["message"]),
        )
    )
    print(
        "- pa_overview: parser_engines={parser_count} parser_available={parser_available} "
        "storage_engines={storage_count} storage_available={storage_available}".format(
            parser_count=sample["parser_engine_count"],
            parser_available=sample["parser_available_count"],
            storage_count=sample["storage_engine_count"],
            storage_available=sample["storage_available_count"],
        )
    )
    print(
        "- sample_parse: status={status} parse_status={parse_status} chunks={chunks} spans_source={source}".format(
            status=sample["status"],
            parse_status=sample["parse_status"],
            chunks=sample["chunk_count"],
            source=sample["spans_source"],
        )
    )
    print(f"- cleanup: document_delete={sample['delete_action']}")
    if browser_mode:
        print("- browser: Capability Center rendered parser/storage status UI")
    print("- output: sanitized")
    return 0 if passed else 1


def _check_parser_engines(native_base_url: str, token: str) -> dict[str, Any]:
    response = _post_json(
        f"{native_base_url}/api/v1/system/parser-engines/check",
        {},
        token,
    )
    engines = response.get("data") if isinstance(response.get("data"), list) else []
    available = [
        item
        for item in engines
        if isinstance(item, dict) and bool(item.get("Available", item.get("available")))
    ]
    return {
        "engine_count": len([item for item in engines if isinstance(item, dict)]),
        "available_count": len(available),
        "connected": bool(response.get("connected")),
    }


def _check_local_storage(native_base_url: str, token: str) -> dict[str, Any]:
    response = _post_json(
        f"{native_base_url}/api/v1/system/storage-engine-check",
        {"provider": "local"},
        token,
    )
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    return {
        "ok": bool(data.get("ok")),
        "message": data.get("message") or response.get("msg") or "",
    }


def _run_sample_parse(*, browser_mode: bool) -> dict[str, Any]:
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-p3-03-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'parser-storage.db'}"
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/model/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "model overview uses native source")
            _assert(bool(overview.get("masked")), "model overview is masked")
            _assert(_no_secret_payload(overview), "model overview excludes secret-shaped fields")
            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            parser_surface = _surface(surfaces, "parser_engines")
            storage_surface = _surface(surfaces, "storage_engines")

            kb_id = _active_or_first_kb_id(
                _request_json(backend_port, "GET", "/api/knowledge-bases/native/overview?limit=10")
            )
            _assert(bool(kb_id), "active KB id is available for sample parse")

            document_id, external_doc_id = _upload_sample_document(backend_port, kb_id, run_id)
            indexed = _wait_until_indexed(backend_port, document_id)
            chunks = _request_json(backend_port, "GET", f"/api/documents/{document_id}/chunks")
            spans = _request_json(backend_port, "GET", f"/api/documents/{document_id}/spans")
            delete = _request_json(backend_port, "DELETE", f"/api/documents/{document_id}")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, temp_path / "chrome-profile")
                for marker in (
                    "Model / embedding / rerank / parser",
                    "parser_engine_count",
                    "storage_engine_count",
                    "/api/model/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            return {
                "indexed": indexed.get("status") == "indexed",
                "status": str(indexed.get("status") or ""),
                "parse_status": str(spans.get("parse_status") or ""),
                "spans_source": str(spans.get("source") or ""),
                "chunk_count": int(chunks.get("total") or 0),
                "external_doc_present": bool(external_doc_id),
                "delete_action": str(delete.get("action") or ""),
                "parser_engine_count": int(parser_surface.get("count") or 0),
                "parser_available_count": int(parser_surface.get("available_count") or 0),
                "storage_engine_count": int(storage_surface.get("count") or 0),
                "storage_available_count": int(storage_surface.get("available_count") or 0),
            }
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _upload_sample_document(port: int, kb_id: str, run_id: str) -> tuple[str, str]:
    body = (
        f"# WNFC P3 03 {run_id}\n\n"
        "This sanitized markdown document validates parser and storage diagnostics.\n"
    ).encode("utf-8")
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnfc-p3-03-{run_id}.md",
        file_content=body,
        fields={
            "title": f"WNFC-P3-03 parser storage {run_id}",
            "document_type": "wnfc_p3_03",
            "source": "wnfc_p3_03_sample",
            "knowledge_base_id": kb_id,
        },
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    document_id = str(document.get("id") or "")
    external_doc_id = str(document.get("external_doc_id") or "")
    _assert(bool(document_id), "PA document id returned")
    _assert(bool(external_doc_id), "native document id returned")
    _assert(document.get("knowledge_backend") == "weknora_api", "sample document uses WeKnora")
    return document_id, external_doc_id


def _wait_until_indexed(port: int, document_id: str, timeout_seconds: float = 180.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_document: dict[str, Any] = {}
    while time.time() < deadline:
        document = _request_json(port, "GET", f"/api/documents/{document_id}")
        last_document = document
        status = str(document.get("status") or "")
        if status == "indexed":
            return document
        if status == "failed":
            raise AssertionError("sample document reached failed status")
        time.sleep(2)
    raise AssertionError(f"sample document did not reach indexed, last_status={last_document.get('status')}")


def _multipart_request(
    *,
    port: int,
    path: str,
    file_name: str,
    file_content: bytes,
    fields: dict[str, str],
) -> dict[str, Any]:
    boundary = f"----pa-wnfc-p3-03-{uuid4().hex}"
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    parts.extend(
        [
            f"--{boundary}\r\n".encode("ascii"),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_name}"\r\n'
                "Content-Type: text/markdown\r\n\r\n"
            ).encode("utf-8"),
            file_content,
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )
    req = request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=b"".join(parts),
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"PA sample upload HTTP {exc.code}: {_safe_message(body)}") from exc


def _post_json(url: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": token,
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"native diagnostic HTTP {exc.code}: {_safe_message(body)}") from exc


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _active_or_first_kb_id(overview: dict[str, Any]) -> str:
    active = overview.get("active_selection")
    if isinstance(active, dict) and active.get("kb_id"):
        return str(active["kb_id"])
    items = overview.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        return str(items[0].get("id") or "")
    return ""


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
            if "Model / embedding / rerank / parser" in dom and "parser_engine_count" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


def _load_local_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env.update(_read_env_file(OUTER_ROOT / ".env"))
    env.update(_read_env_file(PROJECT_ROOT / ".env"))
    env.update(_read_env_file(PROJECT_ROOT / "backend" / ".env"))
    env.update(os.environ)
    return env


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _no_secret_payload(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        '"api_key":',
        '"app_secret":',
        '"authorization":',
        '"password":',
        '"secret_access_key":',
        '"docreader_addr":',
        '"base_url":',
        '"defaulturls":',
        '"custom_headers":',
    ]
    return not any(token in serialized for token in forbidden)


def _safe_message(message: Any) -> str:
    cleaned = str(message or "")
    for marker in (
        "sk-",
        "Bearer ",
        "Authorization",
        "apiKey",
        "api_key",
        "token",
        "secret",
        "password",
        "docreader_addr",
        "base_url",
    ):
        cleaned = cleaned.replace(marker, "[redacted]")
    return cleaned[:220]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("WeKnora native parser/storage diagnostics", file=sys.stderr)
        print("- decision: BLOCKED", file=sys.stderr)
        print("- evidence_type: blocked evidence plus live api", file=sys.stderr)
        print(f"- blocker: {_safe_message(str(exc))}", file=sys.stderr)
        raise SystemExit(1)
