"""Live WNFC-P3-02 model, embedding, and rerank active tests.

This smoke calls native WeKnora Admin active-test endpoints with the local
real provider configuration. It prints only sanitized availability metadata:
no API keys, service tokens, raw request bodies, or provider payloads.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib import error
from urllib import request


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTER_ROOT = PROJECT_ROOT.parent
NATIVE_BASE_URL = "http://127.0.0.1:8080"


def main() -> int:
    env = _load_local_env()
    token = str(env.get("WEKNORA_SERVICE_TOKEN") or "").strip()
    native_base_url = str(env.get("WEKNORA_BASE_URL") or NATIVE_BASE_URL).rstrip("/")
    print("WeKnora native model/embedding/rerank active tests")
    if not token:
        print("- decision: BLOCKED")
        print("- evidence_type: blocked evidence plus live api preflight")
        print("- blocker: WEKNORA_SERVICE_TOKEN is not configured")
        return 1

    checks = [
        _check_chat(env, native_base_url, token),
        _check_embedding(env, native_base_url, token),
        _check_rerank(env, native_base_url, token),
    ]
    decision = "PASS" if all(check["available"] for check in checks) else "BLOCKED"
    print(f"- decision: {decision}")
    print(
        "- evidence_type: "
        + ("live api" if decision == "PASS" else "blocked evidence plus live api")
    )
    for check in checks:
        details = f"available={str(check['available']).lower()}"
        if check.get("dimension"):
            details += f" dimension={check['dimension']}"
        if check.get("missing"):
            details += f" missing={','.join(check['missing'])}"
        print(f"- {check['name']}: {details} message={_safe_message(check.get('message'))}")
    print("- output: sanitized")
    return 0 if decision == "PASS" else 1


def _check_chat(env: dict[str, str], base_url: str, token: str) -> dict[str, Any]:
    payload = {
        "source": "remote",
        "modelName": str(env.get("CHAT_MODEL_NAME") or ""),
        "baseUrl": str(env.get("CHAT_MODEL_BASE_URL") or ""),
        "apiKey": str(env.get("CHAT_MODEL_API_KEY") or ""),
        "provider": str(env.get("CHAT_MODEL_PROVIDER") or ""),
    }
    return _run_check(
        name="chat",
        url=f"{base_url}/api/v1/initialization/remote/check",
        payload=payload,
        token=token,
    )


def _check_embedding(env: dict[str, str], base_url: str, token: str) -> dict[str, Any]:
    payload = {
        "source": "remote",
        "modelName": str(env.get("EMBEDDING_MODEL_NAME") or ""),
        "baseUrl": str(env.get("EMBEDDING_BASE_URL") or ""),
        "apiKey": str(env.get("EMBEDDING_API_KEY") or ""),
        "provider": str(env.get("EMBEDDING_PROVIDER") or ""),
        "dimension": _safe_int(env.get("EMBEDDING_DIMENSION")),
    }
    return _run_check(
        name="embedding",
        url=f"{base_url}/api/v1/initialization/embedding/test",
        payload=payload,
        token=token,
    )


def _check_rerank(env: dict[str, str], base_url: str, token: str) -> dict[str, Any]:
    payload = {
        "source": "remote",
        "modelName": str(env.get("RERANK_MODEL_NAME") or "qwen3-rerank"),
        "baseUrl": str(
            env.get("RERANK_BASE_URL")
            or "https://dashscope.aliyuncs.com/compatible-api/v1"
        ),
        "apiKey": str(env.get("RERANK_API_KEY") or env.get("DASHSCOPE_API_KEY") or ""),
        "provider": str(env.get("RERANK_PROVIDER") or "aliyun"),
    }
    return _run_check(
        name="rerank",
        url=f"{base_url}/api/v1/initialization/rerank/check",
        payload=payload,
        token=token,
    )


def _run_check(name: str, url: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    missing = [
        key
        for key in ("modelName", "baseUrl", "apiKey", "provider")
        if not str(payload.get(key) or "").strip()
    ]
    if missing:
        return {
            "name": name,
            "available": False,
            "message": "local provider config is incomplete",
            "missing": missing,
        }
    response = _post_json(url, payload, token)
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    return {
        "name": name,
        "available": bool(data.get("available")),
        "dimension": data.get("dimension"),
        "message": data.get("message") or response.get("message") or "",
    }


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
        with request.urlopen(req, timeout=80) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {
            "success": False,
            "data": {
                "available": False,
                "message": f"native active test HTTP {exc.code}: {_safe_message(body)}",
            },
        }
    except error.URLError as exc:
        return {
            "success": False,
            "data": {
                "available": False,
                "message": f"native active test network error: {_safe_message(str(exc))}",
            },
        }


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


def _safe_int(value: str | None) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


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
    ):
        cleaned = cleaned.replace(marker, "[redacted]")
    return cleaned[:240]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("WeKnora native model/embedding/rerank active tests", file=sys.stderr)
        print("- decision: BLOCKED", file=sys.stderr)
        print("- evidence_type: blocked evidence plus live api", file=sys.stderr)
        print(f"- blocker: {_safe_message(str(exc))}", file=sys.stderr)
        raise SystemExit(1)
