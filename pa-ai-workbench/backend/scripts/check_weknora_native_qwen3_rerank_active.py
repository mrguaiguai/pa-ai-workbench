"""Live WNFC-P3-01 qwen3-rerank active check.

The script calls native WeKnora's Admin rerank check endpoint with the local
Qwen/DashScope rerank configuration. It reads credentials from environment or
the local ignored .env files, prints only availability/message metadata, and
never prints API keys, service tokens, or request payloads.
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


def main() -> int:
    env = {}
    env.update(_read_env_file(OUTER_ROOT / ".env"))
    env.update(_read_env_file(PROJECT_ROOT / "backend" / ".env"))
    env.update(os.environ)

    token = str(env.get("WEKNORA_SERVICE_TOKEN") or "").strip()
    api_key = str(env.get("RERANK_API_KEY") or env.get("DASHSCOPE_API_KEY") or "").strip()
    if not token:
        print("qwen3_rerank_check")
        print("available=false")
        print("message=WEKNORA_SERVICE_TOKEN is not configured")
        return 1
    if not api_key:
        print("qwen3_rerank_check")
        print("available=false")
        print("message=RERANK_API_KEY or DASHSCOPE_API_KEY is not configured")
        return 1

    payload = {
        "source": "remote",
        "modelName": str(env.get("RERANK_MODEL_NAME") or "qwen3-rerank"),
        "baseUrl": str(env.get("RERANK_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-api/v1"),
        "apiKey": api_key,
        "provider": str(env.get("RERANK_PROVIDER") or "aliyun"),
    }
    response = _post_json(
        "http://127.0.0.1:8080/api/v1/initialization/rerank/check",
        payload,
        token,
    )
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    available = bool(data.get("available"))
    message = str(data.get("message") or "")
    print("qwen3_rerank_check")
    print(f"available={str(available).lower()}")
    print(f"message={_safe_message(message)}")
    return 0 if available else 1


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
        raise RuntimeError(f"native rerank check HTTP {exc.code}: {_safe_message(body)}") from exc


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


def _safe_message(message: str) -> str:
    forbidden = ("sk-", "Bearer ", "Authorization", "apiKey", "api_key", "token", "secret", "password")
    cleaned = message
    for marker in forbidden:
        cleaned = cleaned.replace(marker, "[redacted]")
    return cleaned[:220]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("qwen3_rerank_check", file=sys.stderr)
        print("available=false", file=sys.stderr)
        print(f"message={_safe_message(str(exc))}", file=sys.stderr)
        raise SystemExit(1)
