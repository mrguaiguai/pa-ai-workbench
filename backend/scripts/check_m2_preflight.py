"""M2 real runtime preflight gate for PA AI Workbench.

This checker fails closed: unknown runtime state is treated as NOT READY.
It loads PA runtime configuration through environment variables, probes
WeKnora with the configured service token, and never prints secrets, raw
documents, long prompts, or chunk bodies.

Live side effects:
- POST /api/v1/vector-stores/{id}/test probes vector-store connectivity. For
  user-created WeKnora vector stores, WeKnora may save a detected version.
- POST /api/v1/knowledge-search sends one short sanitized query to validate
  embedding/vector dimension compatibility. It may incur one embedding/vector
  lookup. Returned chunks are not printed.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Any
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"

SHORT_QUERY = "P3-M2-A0 preflight vector dimension check"
ASYNC_PROBE_QUERY_PREFIX = "pam2preflightanchor"
VECTOR_STORE_VERSION_SIDE_EFFECT = (
    "POST /api/v1/vector-stores/{id}/test may update WeKnora's detected "
    "vector-store version metadata for user stores"
)
ASYNC_PROBE_SIDE_EFFECT = (
    "POST /api/v1/knowledge-bases/{kb}/knowledge/file uploads one tiny sanitized "
    "Markdown preflight document and polls indexing status to prove Redis/task queue"
)
RETRIEVE_SIDE_EFFECT = (
    "POST /api/v1/knowledge-search sends one short sanitized query; no chunks "
    "or document text are printed"
)


class PreflightError(RuntimeError):
    """Operator-facing failure with sanitized detail."""


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class WeKnoraConfig:
    base_url: str
    service_token: str
    workspace_id: str
    default_kb_id: str
    timeout_seconds: float


class WeKnoraClient:
    def __init__(self, config: WeKnoraConfig) -> None:
        self.config = config

    def get(self, path: str, authenticated: bool = True) -> Any:
        return self.request("GET", path, authenticated=authenticated)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, payload=payload, authenticated=True)

    def post_multipart(
        self,
        path: str,
        file_path: Path,
        fields: dict[str, str],
    ) -> Any:
        boundary = f"----pa-m2-preflight-{uuid4().hex}"
        body = _multipart_body(boundary, file_path, fields)
        headers = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        headers["X-API-Key"] = self.config.service_token
        headers["Authorization"] = f"Bearer {self.config.service_token}"
        if self.config.workspace_id.isdigit():
            headers["X-Tenant-ID"] = self.config.workspace_id

        request = Request(
            url=f"{self.config.base_url}{path}",
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise PreflightError(
                f"POST {path} returned HTTP {exc.code}: {_safe_error(response_body)}"
            ) from exc
        except (TimeoutError, URLError) as exc:
            raise PreflightError(f"POST {path} failed: {_safe_error(str(exc))}") from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PreflightError(f"POST {path} returned invalid JSON") from exc

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated:
            headers["X-API-Key"] = self.config.service_token
            headers["Authorization"] = f"Bearer {self.config.service_token}"
            if self.config.workspace_id.isdigit():
                headers["X-Tenant-ID"] = self.config.workspace_id

        request = Request(
            url=f"{self.config.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise PreflightError(
                f"{method} {path} returned HTTP {exc.code}: {_safe_error(response_body)}"
            ) from exc
        except (TimeoutError, URLError) as exc:
            raise PreflightError(f"{method} {path} failed: {_safe_error(str(exc))}") from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PreflightError(f"{method} {path} returned invalid JSON") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Check M2 real runtime readiness.")
    parser.add_argument(
        "--no-live-probes",
        action="store_true",
        help="Skip live vector/retrieve probes. This intentionally fails readiness.",
    )
    args = parser.parse_args()

    checks = run_checks(run_live_probes=not args.no_live_probes)
    decision = "READY" if all(check.status != FAIL for check in checks) else "NOT READY"

    print("M2 real runtime preflight")
    print(f"- decision: {decision}")
    for check in checks:
        print(f"- {check.name}: {check.status} - {check.detail}")

    return 0 if decision == "READY" else 1


def run_checks(run_live_probes: bool = True) -> list[Check]:
    settings = Settings()
    checks: list[Check] = []

    checks.append(_check_pa_config())
    weknora_config, weknora_env_check = _load_weknora_config(settings)
    checks.append(weknora_env_check)

    client: WeKnoraClient | None = None
    kb_data: dict[str, Any] | None = None
    models: list[dict[str, Any]] = []
    if weknora_config is not None:
        client = WeKnoraClient(weknora_config)
        connection_check, kb_data = _check_weknora_connection(client, weknora_config)
        checks.append(connection_check)
        checks.append(_check_redis(client, weknora_config, run_live_probes))

        model_check, models = _check_weknora_models(client)
        checks.append(model_check)

        if kb_data is not None and models:
            checks.append(_check_kb_knowledgeqa(kb_data, models))
            checks.append(_check_kb_embedding(kb_data, models))
        else:
            checks.append(
                Check(
                    "KB KnowledgeQA binding",
                    FAIL,
                    "requires successful WeKnora KB and model checks",
                )
            )
            checks.append(
                Check(
                    "KB embedding binding",
                    FAIL,
                    "requires successful WeKnora KB and model checks",
                )
            )

        checks.append(_check_docreader(client))
        checks.append(_check_system_info(client))
        checks.append(_check_vector_store(client, kb_data))
        checks.append(_check_dimension_probe(client, weknora_config, run_live_probes))
    else:
        checks.extend(
            [
                Check("Redis/task queue", FAIL, "WeKnora config is incomplete"),
                Check("WeKnora health/auth/workspace/KB", FAIL, "WeKnora config is incomplete"),
                Check("WeKnora models", FAIL, "WeKnora config is incomplete"),
                Check("KB KnowledgeQA binding", FAIL, "WeKnora config is incomplete"),
                Check("KB embedding binding", FAIL, "WeKnora config is incomplete"),
                Check("DocReader", FAIL, "WeKnora config is incomplete"),
                Check("WeKnora system info", FAIL, "WeKnora config is incomplete"),
                Check("Vector store", FAIL, "WeKnora config is incomplete"),
                Check("Vector dimension probe", FAIL, "WeKnora config is incomplete"),
            ]
        )

    checks.append(Check("Live probe side effects", INFO, _side_effect_detail(run_live_probes)))
    return checks


def _check_pa_config() -> Check:
    required_values = {
        "KNOWLEDGE_BACKEND": "weknora_api",
        "MOCK_MODE": "false",
        "CHAT_MODEL_PROVIDER": "openai_compatible",
        "MOCK_MODEL_MODE": "false",
    }
    missing_or_wrong: list[str] = []
    for name, expected in required_values.items():
        value = _env(name)
        if value is None:
            missing_or_wrong.append(f"{name}={expected}")
        elif value.strip().lower() != expected:
            missing_or_wrong.append(f"{name}={expected}")

    for name in ("CHAT_MODEL_BASE_URL", "CHAT_MODEL_API_KEY", "CHAT_MODEL_NAME"):
        if not _env_nonempty(name):
            missing_or_wrong.append(name)

    if missing_or_wrong:
        return Check("PA runtime config", FAIL, "missing/invalid " + ", ".join(missing_or_wrong))
    return Check(
        "PA runtime config",
        PASS,
        "mock disabled; chat provider, base URL, API key, and model name are present",
    )


def _load_weknora_config(settings: Settings) -> tuple[WeKnoraConfig | None, Check]:
    missing = []
    if not settings.weknora_base_url.strip():
        missing.append("WEKNORA_BASE_URL")
    if not settings.weknora_service_token.strip():
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not settings.weknora_workspace_id.strip():
        missing.append("WEKNORA_WORKSPACE_ID")
    if not settings.weknora_default_kb_id.strip():
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if settings.weknora_timeout_seconds <= 0:
        missing.append("WEKNORA_TIMEOUT_SECONDS")

    if missing:
        return None, Check("WeKnora service config", FAIL, "missing " + ", ".join(missing))

    config = WeKnoraConfig(
        base_url=settings.weknora_base_url.rstrip("/"),
        service_token=settings.weknora_service_token,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        timeout_seconds=float(settings.weknora_timeout_seconds),
    )
    return config, Check(
        "WeKnora service config",
        PASS,
        f"service token/workspace/KB configured; base URL {_redacted_url_status(config.base_url)}",
    )


def _check_weknora_connection(
    client: WeKnoraClient,
    config: WeKnoraConfig,
) -> tuple[Check, dict[str, Any] | None]:
    try:
        health = client.get("/health", authenticated=False)
        if not _health_ok(health):
            return Check("WeKnora health/auth/workspace/KB", FAIL, "health returned not-ready"), None

        auth = client.get("/api/v1/auth/me")
        if not _api_success(auth):
            return Check("WeKnora health/auth/workspace/KB", FAIL, "auth check failed"), None

        workspace_path = f"/api/v1/tenants/{quote(config.workspace_id, safe='')}"
        workspace = client.get(workspace_path)
        if not _api_success(workspace):
            return Check("WeKnora health/auth/workspace/KB", FAIL, "workspace check failed"), None

        kb_path = f"/api/v1/knowledge-bases/{quote(config.default_kb_id, safe='')}"
        kb = client.get(kb_path)
        if not _api_success(kb):
            return Check("WeKnora health/auth/workspace/KB", FAIL, "knowledge-base check failed"), None
        kb_data = _unwrap_data(kb)
        if not isinstance(kb_data, dict):
            return Check("WeKnora health/auth/workspace/KB", FAIL, "KB response has no object data"), None
    except PreflightError as exc:
        return Check("WeKnora health/auth/workspace/KB", FAIL, str(exc)), None

    return (
        Check(
            "WeKnora health/auth/workspace/KB",
            PASS,
            f"health/auth/workspace OK; KB id {_safe_id(config.default_kb_id)} reachable",
        ),
        kb_data,
    )


def _check_weknora_models(client: WeKnoraClient) -> tuple[Check, list[dict[str, Any]]]:
    try:
        response = client.get("/api/v1/models")
    except PreflightError as exc:
        return Check("WeKnora models", FAIL, str(exc)), []

    items = _items(response)
    if not items:
        return Check("WeKnora models", FAIL, "model list is empty or unavailable"), []

    active_models = [model for model in items if _model_active(model)]
    kqa_models = [model for model in active_models if _model_type(model) == "knowledgeqa"]
    embedding_models = [model for model in active_models if _model_type(model) == "embedding"]

    deepseek_kqa = [model for model in kqa_models if _is_deepseek_model(model)]
    dashscope_embedding = [model for model in embedding_models if _is_dashscope_model(model)]

    if not deepseek_kqa:
        return Check("WeKnora models", FAIL, "no active KnowledgeQA model using DeepSeek"), items
    if _default_models(kqa_models) and not _default_models(deepseek_kqa):
        return Check("WeKnora models", FAIL, "default KnowledgeQA model is not DeepSeek"), items
    missing_kqa_credentials = [
        _safe_id(str(model.get("id") or ""))
        for model in deepseek_kqa
        if not _model_has_api_key(model)
    ]
    if missing_kqa_credentials:
        return Check(
            "WeKnora models",
            FAIL,
            "DeepSeek KnowledgeQA model lacks configured API key metadata: "
            + ", ".join(missing_kqa_credentials),
        ), items
    if not dashscope_embedding:
        return Check("WeKnora models", FAIL, "no active Embedding model using DashScope/Aliyun"), items
    missing_embedding_credentials = [
        _safe_id(str(model.get("id") or ""))
        for model in dashscope_embedding
        if not _model_has_api_key(model)
    ]
    if missing_embedding_credentials:
        return Check(
            "WeKnora models",
            FAIL,
            "DashScope/Aliyun Embedding model lacks configured API key metadata: "
            + ", ".join(missing_embedding_credentials),
        ), items
    bad_dims = [
        _safe_id(str(model.get("id") or ""))
        for model in dashscope_embedding
        if _embedding_dimension(model) <= 0
    ]
    if bad_dims:
        return Check(
            "WeKnora models",
            FAIL,
            "DashScope embedding model has missing/non-positive dimension: " + ", ".join(bad_dims),
        ), items

    return (
        Check(
            "WeKnora models",
            PASS,
            (
                "DeepSeek KnowledgeQA and DashScope/Aliyun Embedding model records found; "
                "credentials are not printed"
            ),
        ),
        items,
    )


def _check_kb_knowledgeqa(kb_data: dict[str, Any], models: list[dict[str, Any]]) -> Check:
    summary_model_id = str(
        kb_data.get("summary_model_id")
        or kb_data.get("llm_model_id")
        or kb_data.get("model_id")
        or ""
    ).strip()
    if summary_model_id:
        model = _model_by_id(models, summary_model_id)
        if model is None:
            return Check(
                "KB KnowledgeQA binding",
                FAIL,
                f"KB KnowledgeQA model {_safe_id(summary_model_id)} is not in model list",
            )
        if _model_type(model) != "knowledgeqa":
            return Check("KB KnowledgeQA binding", FAIL, "KB KnowledgeQA binding is not a KnowledgeQA model")
        if not _is_deepseek_model(model):
            return Check("KB KnowledgeQA binding", FAIL, "KB KnowledgeQA binding is not DeepSeek")
        if not _model_has_api_key(model):
            return Check("KB KnowledgeQA binding", FAIL, "KB KnowledgeQA model lacks API key metadata")
        return Check(
            "KB KnowledgeQA binding",
            PASS,
            f"KB binds DeepSeek KnowledgeQA model {_safe_id(summary_model_id)}",
        )

    default_deepseek = [
        model
        for model in models
        if _model_type(model) == "knowledgeqa" and _model_active(model) and _is_deepseek_model(model)
    ]
    if _default_models(default_deepseek):
        return Check(
            "KB KnowledgeQA binding",
            PASS,
            "KB has no explicit KnowledgeQA binding; default DeepSeek KnowledgeQA is available",
        )
    return Check("KB KnowledgeQA binding", FAIL, "KB has no KnowledgeQA binding and no default DeepSeek model")


def _check_kb_embedding(kb_data: dict[str, Any], models: list[dict[str, Any]]) -> Check:
    embedding_model_id = str(kb_data.get("embedding_model_id") or "").strip()
    if not embedding_model_id:
        return Check("KB embedding binding", FAIL, "KB has no embedding_model_id")

    model = _model_by_id(models, embedding_model_id)
    if model is None:
        return Check(
            "KB embedding binding",
            FAIL,
            f"KB embedding_model_id {_safe_id(embedding_model_id)} is not in model list",
        )
    if _model_type(model) != "embedding":
        return Check("KB embedding binding", FAIL, "KB embedding_model_id is not an Embedding model")
    if not _is_dashscope_model(model):
        return Check("KB embedding binding", FAIL, "KB embedding model is not DashScope/Aliyun")
    if not _model_has_api_key(model):
        return Check("KB embedding binding", FAIL, "KB embedding model lacks API key metadata")
    dimension = _embedding_dimension(model)
    if dimension <= 0:
        return Check("KB embedding binding", FAIL, "KB embedding model dimension is missing")

    return Check(
        "KB embedding binding",
        PASS,
        f"KB binds DashScope/Aliyun embedding model {_safe_id(embedding_model_id)} with dimension {dimension}",
    )


def _check_docreader(client: WeKnoraClient) -> Check:
    try:
        response = client.get("/api/v1/system/parser-engines")
    except PreflightError as exc:
        return Check("DocReader", FAIL, str(exc))

    if not _code_success(response):
        return Check("DocReader", FAIL, "parser engine endpoint did not return success")
    if not bool(_case_get(response, "connected")):
        return Check("DocReader", FAIL, "docreader connected=false")
    engines = _unwrap_data(response)
    if not isinstance(engines, list) or not engines:
        return Check("DocReader", FAIL, "no parser engines reported")
    return Check("DocReader", PASS, f"connected; {len(engines)} parser engine(s) reported")


def _check_system_info(client: WeKnoraClient) -> Check:
    try:
        response = client.get("/api/v1/system/info")
    except PreflightError as exc:
        return Check("WeKnora system info", FAIL, str(exc))

    if not _code_success(response):
        return Check("WeKnora system info", FAIL, "system info endpoint did not return success")
    data = _unwrap_data(response)
    if not isinstance(data, dict):
        return Check("WeKnora system info", FAIL, "system info returned no data object")
    migration_error = str(data.get("db_migration_error") or "").strip()
    if migration_error:
        return Check("WeKnora system info", FAIL, "database migration error is present")
    vector_engine = str(data.get("vector_store_engine") or "").strip()
    if not vector_engine or vector_engine in {"未配置", "Not Enabled"}:
        return Check("WeKnora system info", FAIL, "vector store engine is not configured")
    return Check("WeKnora system info", PASS, f"vector engine reported as {_safe_token(vector_engine)}")


def _check_vector_store(client: WeKnoraClient, kb_data: dict[str, Any] | None) -> Check:
    if kb_data is None:
        return Check("Vector store", FAIL, "requires successful KB check")
    try:
        stores_response = client.get("/api/v1/vector-stores")
    except PreflightError as exc:
        return Check("Vector store", FAIL, str(exc))

    stores = _items(stores_response)
    if not stores:
        return Check("Vector store", FAIL, "no vector stores are visible to service account")

    kb_store_id = str(kb_data.get("vector_store_id") or "").strip()
    selected_store = _select_vector_store(stores, kb_store_id)
    if selected_store is None:
        if kb_store_id:
            return Check(
                "Vector store",
                FAIL,
                f"KB vector_store_id {_safe_id(kb_store_id)} is not visible",
            )
        return Check("Vector store", FAIL, "no env/default vector store is visible")

    store_id = str(selected_store.get("id") or "").strip()
    if not store_id:
        return Check("Vector store", FAIL, "selected vector store has no id")

    try:
        response = client.post(f"/api/v1/vector-stores/{quote(store_id, safe='')}/test", {})
    except PreflightError as exc:
        return Check("Vector store", FAIL, str(exc))
    if not _api_success(response):
        return Check("Vector store", FAIL, "vector store live test returned failure")

    engine = str(selected_store.get("engine_type") or selected_store.get("engineType") or "unknown")
    detail = (
        f"{_safe_token(engine)} store {_safe_id(store_id)} live test passed; "
        f"{VECTOR_STORE_VERSION_SIDE_EFFECT}"
    )
    return Check("Vector store", PASS, detail)


def _check_dimension_probe(
    client: WeKnoraClient,
    config: WeKnoraConfig,
    run_live_probes: bool,
) -> Check:
    if not run_live_probes:
        return Check(
            "Vector dimension probe",
            FAIL,
            "live retrieve probe skipped; fail-closed because dimension mismatch cannot be ruled out",
        )
    payload = {
        "query": SHORT_QUERY,
        "knowledge_base_ids": [config.default_kb_id],
    }
    try:
        response = client.post("/api/v1/knowledge-search", payload)
    except PreflightError as exc:
        return Check("Vector dimension probe", FAIL, str(exc))

    if not _api_success(response):
        return Check("Vector dimension probe", FAIL, "knowledge-search probe returned failure")
    data = _unwrap_data(response)
    if not isinstance(data, (list, dict)):
        return Check("Vector dimension probe", FAIL, "knowledge-search returned unexpected data shape")
    return Check(
        "Vector dimension probe",
        PASS,
        "embedding/vector query completed; dimension mismatch was not reported",
    )


def _check_redis(
    client: WeKnoraClient,
    config: WeKnoraConfig,
    run_live_probes: bool,
) -> Check:
    direct = _check_redis_direct()
    if direct.status == PASS:
        return direct
    if not run_live_probes:
        return Check(
            "Redis/task queue",
            FAIL,
            direct.detail + "; async upload/index probe skipped by --no-live-probes",
        )
    return _check_async_indexing_probe(client, config, direct.detail)


def _check_redis_direct() -> Check:
    addr = _env("WEKNORA_REDIS_ADDR") or _env("REDIS_ADDR")
    if not addr:
        return _check_redis_container()
    username = _env("WEKNORA_REDIS_USERNAME") or _env("REDIS_USERNAME") or ""
    password = _env("WEKNORA_REDIS_PASSWORD") or _env("REDIS_PASSWORD") or ""
    db_raw = _env("WEKNORA_REDIS_DB") or _env("REDIS_DB") or "0"
    try:
        db = int(db_raw)
    except ValueError:
        return Check("Redis/task queue", FAIL, "REDIS_DB/WEKNORA_REDIS_DB is not an integer")

    try:
        _redis_ping(addr, username=username, password=password, db=db)
    except PreflightError as exc:
        return Check("Redis/task queue", FAIL, str(exc))
    return Check("Redis/task queue", PASS, "direct Redis PING succeeded; credentials not printed")


def _multipart_body(boundary: str, file_path: Path, fields: dict[str, str]) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    file_bytes = file_path.read_bytes()
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8")
    )
    chunks.append(b"Content-Type: text/markdown\r\n\r\n")
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def _write_async_probe_fixture(path: Path, run_id: str, anchor: str) -> None:
    path.write_text(
        "\n".join(
            [
                "# PA M2 Preflight Sanitized Fixture",
                "",
                "This synthetic document contains no real pilot data.",
                f"The preflight run id is {run_id}.",
                f"The retrieval anchor is {anchor}.",
                "A passing preflight indexes this short fixture through WeKnora.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _wait_for_indexed(
    client: WeKnoraClient,
    external_doc_id: str,
    wait_seconds: int,
    poll_seconds: int,
) -> str:
    deadline = time.monotonic() + wait_seconds
    last_status = "unknown"
    while time.monotonic() <= deadline:
        status_response = client.get(f"/api/v1/knowledge/{quote(external_doc_id, safe='')}")
        status_data = _unwrap_data(status_response)
        if not isinstance(status_data, dict):
            raise PreflightError("document status returned no object data")
        raw_status = str(
            status_data.get("parse_status") or status_data.get("status") or "unknown"
        ).strip()
        normalized = raw_status.lower()
        last_status = normalized or "unknown"
        if normalized in {"completed", "indexed", "ready"}:
            return normalized
        if normalized in {"failed", "error", "cancelled"}:
            raise PreflightError("document indexing failed")
        time.sleep(poll_seconds)
    raise PreflightError(
        f"document did not reach indexed within {wait_seconds}s; last status {last_status}"
    )


def _check_redis_container() -> Check:
    container = (_env("WEKNORA_REDIS_CONTAINER") or "WeKnora-redis").strip()
    if not container:
        return Check(
            "Redis/task queue",
            FAIL,
            "REDIS_ADDR/WEKNORA_REDIS_ADDR is not visible and no Redis container is configured",
        )
    command = [
        "docker",
        "exec",
        container,
        "sh",
        "-lc",
        'if [ -n "$REDIS_PASSWORD" ]; then redis-cli -a "$REDIS_PASSWORD" PING; else redis-cli PING; fi',
    ]
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check(
            "Redis/task queue",
            FAIL,
            "direct Redis env is absent and Docker Redis PING failed: " + _safe_error(str(exc)),
        )
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode == 0 and "PONG" in output:
        return Check(
            "Redis/task queue",
            PASS,
            f"Docker container {_safe_id(container)} PING succeeded; password not printed",
        )
    return Check(
        "Redis/task queue",
        FAIL,
        "direct Redis env is absent and Docker Redis PING failed: " + _safe_error(output),
    )


def _check_async_indexing_probe(
    client: WeKnoraClient,
    config: WeKnoraConfig,
    direct_failure_detail: str,
) -> Check:
    wait_seconds = _int_env("M2_PREFLIGHT_ASYNC_WAIT_SECONDS", 180)
    poll_seconds = _int_env("M2_PREFLIGHT_ASYNC_POLL_SECONDS", 5)
    if wait_seconds <= 0 or poll_seconds <= 0:
        return Check("Redis/task queue", FAIL, "async probe wait/poll env must be positive")

    run_id = uuid4().hex[:12]
    anchor = f"{ASYNC_PROBE_QUERY_PREFIX}{run_id}"
    try:
        with TemporaryDirectory(prefix="pa-m2-preflight-") as temp_dir:
            path = Path(temp_dir) / f"pa-m2-preflight-sanitized-{run_id}.md"
            _write_async_probe_fixture(path, run_id, anchor)
            upload = client.post_multipart(
                f"/api/v1/knowledge-bases/{quote(config.default_kb_id, safe='')}/knowledge/file",
                path,
                fields={
                    "fileName": path.name,
                    "channel": "api",
                    "metadata": json.dumps(
                        {
                            "source": "pa_m2_preflight",
                            "task": "P3-M2-A0",
                            "fixture": "sanitized",
                        },
                        ensure_ascii=False,
                    ),
                },
            )
    except PreflightError as exc:
        return Check("Redis/task queue", FAIL, f"async upload probe failed: {exc}")

    upload_data = _unwrap_data(upload)
    if not isinstance(upload_data, dict):
        return Check("Redis/task queue", FAIL, "async upload probe returned no document object")
    external_doc_id = str(upload_data.get("id") or upload_data.get("external_doc_id") or "").strip()
    if not external_doc_id:
        return Check("Redis/task queue", FAIL, "async upload probe returned no document id")

    try:
        status = _wait_for_indexed(client, external_doc_id, wait_seconds, poll_seconds)
    except PreflightError as exc:
        return Check("Redis/task queue", FAIL, f"async indexing probe failed: {exc}")

    detail = (
        f"async sanitized upload reached {status}; Redis/task queue proven via WeKnora indexing. "
        f"Direct Redis check was unavailable: {_safe_error(direct_failure_detail)}"
    )
    return Check("Redis/task queue", PASS, detail)


def _redis_ping(addr: str, username: str, password: str, db: int) -> None:
    host, port = _parse_redis_addr(addr)
    try:
        with socket.create_connection((host, port), timeout=5.0) as sock:
            sock.settimeout(5.0)
            if password:
                if username:
                    _redis_expect_ok(sock, ["AUTH", username, password])
                else:
                    _redis_expect_ok(sock, ["AUTH", password])
            if db:
                _redis_expect_ok(sock, ["SELECT", str(db)])
            _redis_expect_pong(sock)
    except OSError as exc:
        raise PreflightError(f"Redis PING failed: {_safe_error(str(exc))}") from exc


def _parse_redis_addr(addr: str) -> tuple[str, int]:
    value = addr.strip()
    if "://" in value:
        parsed = urlparse(value)
        if not parsed.hostname:
            raise PreflightError("Redis address is invalid")
        return parsed.hostname, parsed.port or 6379
    if ":" in value:
        host, port_raw = value.rsplit(":", 1)
        try:
            return host.strip(), int(port_raw)
        except ValueError as exc:
            raise PreflightError("Redis address port is invalid") from exc
    return value, 6379


def _redis_command(parts: list[str]) -> bytes:
    chunks = [f"*{len(parts)}\r\n".encode("utf-8")]
    for part in parts:
        encoded = part.encode("utf-8")
        chunks.append(f"${len(encoded)}\r\n".encode("utf-8"))
        chunks.append(encoded + b"\r\n")
    return b"".join(chunks)


def _redis_read_line(sock: socket.socket) -> bytes:
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise PreflightError("Redis closed the connection")
        data.extend(chunk)
        if data.endswith(b"\r\n"):
            return bytes(data[:-2])


def _redis_expect_ok(sock: socket.socket, parts: list[str]) -> None:
    sock.sendall(_redis_command(parts))
    line = _redis_read_line(sock)
    if line != b"+OK":
        raise PreflightError("Redis command failed")


def _redis_expect_pong(sock: socket.socket) -> None:
    sock.sendall(_redis_command(["PING"]))
    line = _redis_read_line(sock)
    if line != b"+PONG":
        raise PreflightError("Redis PING did not return PONG")


def _side_effect_detail(run_live_probes: bool) -> str:
    if not run_live_probes:
        return "live probes skipped by flag; readiness intentionally fails"
    return (
        VECTOR_STORE_VERSION_SIDE_EFFECT
        + "; "
        + ASYNC_PROBE_SIDE_EFFECT
        + "; "
        + RETRIEVE_SIDE_EFFECT
    )


def _select_vector_store(stores: list[dict[str, Any]], kb_store_id: str) -> dict[str, Any] | None:
    if kb_store_id:
        return next((store for store in stores if str(store.get("id") or "") == kb_store_id), None)
    env_stores = [
        store
        for store in stores
        if str(store.get("source") or "").lower() == "env"
        or str(store.get("id") or "").startswith("__env_")
    ]
    if env_stores:
        return env_stores[0]
    return stores[0] if stores else None


def _items(response: Any) -> list[dict[str, Any]]:
    data = _unwrap_data(response)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "results", "models", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _unwrap_data(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response.get("data")
    return response


def _api_success(response: Any) -> bool:
    if not isinstance(response, dict):
        return isinstance(response, list)
    if response.get("success") is True:
        return True
    if response.get("success") is False:
        return False
    if response.get("code") == 0:
        return True
    return "data" in response


def _code_success(response: Any) -> bool:
    return isinstance(response, dict) and (
        response.get("code") == 0 or response.get("success") is True
    )


def _health_ok(response: Any) -> bool:
    if not isinstance(response, dict):
        return False
    if _api_success(response):
        return True
    status = str(response.get("status") or "").strip().lower()
    return status in {"ok", "healthy", "success"}


def _case_get(value: dict[str, Any], key: str) -> Any:
    if key in value:
        return value[key]
    camel = "".join([key.split("_")[0], *[part.title() for part in key.split("_")[1:]]])
    return value.get(camel)


def _model_type(model: dict[str, Any]) -> str:
    return str(model.get("type") or "").strip().lower()


def _model_active(model: dict[str, Any]) -> bool:
    status = str(model.get("status") or "active").strip().lower()
    return status in {"", "active"}


def _default_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [model for model in models if bool(model.get("is_default") or model.get("isDefault"))]


def _model_by_id(models: list[dict[str, Any]], model_id: str) -> dict[str, Any] | None:
    return next((model for model in models if str(model.get("id") or "") == model_id), None)


def _model_has_api_key(model: dict[str, Any]) -> bool:
    if bool(model.get("is_builtin") or model.get("isBuiltin")):
        return True
    credentials = model.get("credentials")
    if not isinstance(credentials, dict):
        return False
    api_key = credentials.get("api_key") or credentials.get("apiKey")
    return isinstance(api_key, dict) and bool(api_key.get("configured"))


def _model_haystack(model: dict[str, Any]) -> str:
    params = model.get("parameters")
    if not isinstance(params, dict):
        params = {}
    parts = [
        model.get("name"),
        model.get("display_name"),
        model.get("source"),
        params.get("provider"),
        params.get("base_url"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _is_deepseek_model(model: dict[str, Any]) -> bool:
    source = str(model.get("source") or "").strip().lower()
    if source == "deepseek":
        return True
    return "deepseek" in _model_haystack(model)


def _is_dashscope_model(model: dict[str, Any]) -> bool:
    source = str(model.get("source") or "").strip().lower()
    if source == "aliyun":
        return True
    haystack = _model_haystack(model)
    return "dashscope" in haystack or "aliyun" in haystack or "alibaba" in haystack


def _embedding_dimension(model: dict[str, Any]) -> int:
    params = model.get("parameters")
    if not isinstance(params, dict):
        return 0
    embedding_params = params.get("embedding_parameters")
    if not isinstance(embedding_params, dict):
        return 0
    value = embedding_params.get("dimension")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _env(name: str) -> str | None:
    return os.getenv(name)


def _env_nonempty(name: str) -> bool:
    value = _env(name)
    return value is not None and bool(value.strip())


def _int_env(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _redacted_url_status(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return "configured (scheme unknown)"
    return f"configured (scheme={parsed.scheme}, host redacted)"


def _safe_id(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return "<empty>"
    if len(stripped) <= 12:
        return stripped
    return stripped[:6] + "..." + stripped[-4:]


def _safe_token(value: str, limit: int = 80) -> str:
    collapsed = " ".join(str(value or "").split())
    collapsed = re.sub(r"[^A-Za-z0-9_.,: /+-]", "?", collapsed)
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _safe_error(value: str, limit: int = 180) -> str:
    sanitized = str(value or "")
    sanitized = re.sub(
        r'(?i)("?(?:api[_-]?key|token|authorization|password|secret)"?\s*[:=]\s*)"?[^",\s}]+"?',
        r"\1<redacted>",
        sanitized,
    )
    sanitized = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1<redacted>", sanitized)
    sanitized = re.sub(r"(?i)(x-api-key[:=]\s*)[A-Za-z0-9._~+/=-]+", r"\1<redacted>", sanitized)
    sanitized = re.sub(
        r"https?://[^\s\"'>)]+",
        lambda match: _redact_url(match.group(0)),
        sanitized,
    )
    collapsed = " ".join(sanitized.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return "<url redacted>"
    return f"{parsed.scheme}://<host redacted>"


if __name__ == "__main__":
    raise SystemExit(main())
