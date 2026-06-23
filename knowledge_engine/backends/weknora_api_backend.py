import json
import logging
import mimetypes
import os
import re
import socket
import time
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.errors import WeKnoraAuthError
from knowledge_engine.errors import WeKnoraNetworkError
from knowledge_engine.errors import WeKnoraNotFoundError
from knowledge_engine.errors import WeKnoraRateLimitError
from knowledge_engine.errors import WeKnoraResponseMappingError
from knowledge_engine.errors import WeKnoraServerError
from knowledge_engine.errors import WeKnoraTimeoutError
from knowledge_engine.errors import WeKnoraUnavailableError
from knowledge_engine.kb_mapping import KbMappingResolver
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary
from knowledge_engine.log_context import current_weknora_log_context
from knowledge_engine.retrieval import RETRIEVAL_OPTIONS_KEY
from knowledge_engine.retrieval import normalize_retrieval_options
from knowledge_engine.retrieval import retrieval_debug_trace
from knowledge_engine.retrieval import retrieval_options_payload


WEKNORA_LOGGER = logging.getLogger("pa_ai_workbench.weknora")
WEKNORA_LOGGER.addHandler(logging.NullHandler())
WEKNORA_LOG_EXCERPT_LIMIT = 160


def _get_timeout_seconds(default: float) -> float:
    value = os.getenv("WEKNORA_TIMEOUT_SECONDS")
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_retry_attempts(default: int) -> int:
    value = os.getenv("WEKNORA_RETRY_ATTEMPTS")
    if value is None:
        return default
    try:
        return max(int(value), 0)
    except ValueError:
        return default


def _get_retry_backoff_seconds(default: float) -> float:
    value = os.getenv("WEKNORA_RETRY_BACKOFF_SECONDS")
    if value is None:
        return default
    try:
        return max(float(value), 0.0)
    except ValueError:
        return default


class WeKnoraNativeClient:
    """Shared low-level WeKnora client for native PA integration paths."""

    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        timeout: float,
        retry_attempts: int,
        retry_backoff_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.timeout = timeout
        self.retry_attempts = max(retry_attempts, 0)
        self.retry_backoff_seconds = max(retry_backoff_seconds, 0.0)

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def status(
        self,
        *,
        workspace_id: str | None = None,
        default_kb_id: str | None = None,
    ) -> dict:
        return {
            "schema_version": "wnx-p0-01",
            "source": "weknora_api",
            "client": self.__class__.__name__,
            "status": "configured" if self.configured else "missing_config",
            "configured": self.configured,
            "base_url_configured": bool(self.base_url),
            "service_token_configured": bool(self.service_token),
            "workspace_configured": bool(str(workspace_id or "").strip()),
            "kb_configured": bool(str(default_kb_id or "").strip()),
            "timeout_seconds": self.timeout,
            "retry_attempts": self.retry_attempts,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "trace_id_supported": True,
            "safe_error_shape": "WeKnoraUnavailableError.to_public_dict",
        }

    def request_json(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        self._apply_auth_headers(headers)

        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        return self._perform_json_request(request, operation=f"{method} {path}")

    def request_bytes(self, method: str, path: str) -> tuple[bytes, dict[str, str]]:
        headers = {"Accept": "*/*"}
        self._apply_auth_headers(headers)
        request = Request(
            url=f"{self.base_url}{path}",
            headers=headers,
            method=method,
        )
        return self._perform_bytes_request(request, operation=f"{method} {path}")

    def request_multipart_json(
        self,
        path: str,
        file_path: Path,
        fields: dict[str, str],
    ) -> dict | list:
        boundary = f"----pa-weknora-{uuid4().hex}"
        body = _multipart_body(boundary=boundary, file_path=file_path, fields=fields)
        headers = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        self._apply_auth_headers(headers)
        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method="POST",
        )
        return self._perform_json_request(request, operation=f"POST {path}")

    def request_sse_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> list[dict]:
        body = None
        headers = {"Accept": "text/event-stream"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        self._apply_auth_headers(headers)
        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        operation = _sanitize_operation(f"{method} {path}")
        request_id = uuid4().hex
        started = time.perf_counter()
        events: list[dict] = []
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload_text = line[5:].strip()
                    if not payload_text or payload_text == "[DONE]":
                        continue
                    try:
                        event_payload = json.loads(payload_text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event_payload, dict):
                        events.append(event_payload)
                        if event_payload.get("response_type") == "complete":
                            break
                _log_weknora_call(
                    request_id=request_id,
                    operation=operation,
                    status="ok",
                    status_code=status_code,
                    duration_ms=_elapsed_ms(started),
                    retry_count=0,
                )
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            error = _http_error_to_weknora_error(exc.code, body_text, operation)
            _log_weknora_call(
                request_id=request_id,
                operation=operation,
                status="error",
                status_code=error.status_code,
                duration_ms=_elapsed_ms(started),
                retry_count=0,
                error_code=error.error_code,
                excerpt=error.message,
            )
            raise error from exc
        except (TimeoutError, socket.timeout) as exc:
            error = WeKnoraTimeoutError(
                "WeKnora SSE request timed out",
                error_code="weknora_timeout",
                operation=operation,
                retryable=True,
            )
            _log_weknora_call(
                request_id=request_id,
                operation=operation,
                status="error",
                duration_ms=_elapsed_ms(started),
                retry_count=0,
                error_code=error.error_code,
                excerpt=error.message,
            )
            raise error from exc
        except URLError as exc:
            if _url_error_is_timeout(exc):
                error = WeKnoraTimeoutError(
                    "WeKnora SSE request timed out",
                    error_code="weknora_timeout",
                    operation=operation,
                    retryable=True,
                )
            else:
                error = WeKnoraNetworkError(
                    "WeKnora SSE request failed",
                    error_code="weknora_network_error",
                    operation=operation,
                    retryable=True,
                )
            _log_weknora_call(
                request_id=request_id,
                operation=operation,
                status="error",
                duration_ms=_elapsed_ms(started),
                retry_count=0,
                error_code=error.error_code,
                excerpt=error.message,
            )
            raise error from exc
        return events

    def _perform_json_request(self, request: Request, operation: str) -> dict | list:
        attempts = self.retry_attempts + 1
        last_error: WeKnoraUnavailableError | None = None
        request_id = uuid4().hex
        started = time.perf_counter()
        safe_operation = _sanitize_operation(operation)
        for attempt in range(attempts):
            try:
                raw, status_code = self._read_response(request, safe_operation)
                if not raw:
                    _log_weknora_call(
                        request_id=request_id,
                        operation=safe_operation,
                        status="ok",
                        status_code=status_code,
                        duration_ms=_elapsed_ms(started),
                        retry_count=attempt,
                    )
                    return {}
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise WeKnoraResponseMappingError(
                        "WeKnora returned invalid JSON",
                        error_code="weknora_invalid_json",
                        operation=safe_operation,
                        retryable=False,
                    ) from exc
                _log_weknora_call(
                    request_id=request_id,
                    operation=safe_operation,
                    status="ok",
                    status_code=status_code,
                    duration_ms=_elapsed_ms(started),
                    retry_count=attempt,
                    excerpt=_log_excerpt(raw),
                )
                return data
            except WeKnoraUnavailableError as exc:
                last_error = exc
                if not exc.retryable or attempt >= attempts - 1:
                    _log_weknora_call(
                        request_id=request_id,
                        operation=safe_operation,
                        status="error",
                        status_code=exc.status_code,
                        duration_ms=_elapsed_ms(started),
                        retry_count=attempt,
                        error_code=exc.error_code,
                        excerpt=exc.message,
                    )
                    raise
                self._sleep_before_retry(attempt)
        if last_error is not None:
            raise last_error
        raise WeKnoraUnavailableError(
            "WeKnora request failed",
            operation=_sanitize_operation(operation),
            retryable=False,
        )

    def _perform_bytes_request(self, request: Request, operation: str) -> tuple[bytes, dict[str, str]]:
        attempts = self.retry_attempts + 1
        last_error: WeKnoraUnavailableError | None = None
        request_id = uuid4().hex
        started = time.perf_counter()
        safe_operation = _sanitize_operation(operation)
        for attempt in range(attempts):
            try:
                data, headers, status_code = self._read_bytes_response(request, safe_operation)
                _log_weknora_call(
                    request_id=request_id,
                    operation=safe_operation,
                    status="ok",
                    status_code=status_code,
                    duration_ms=_elapsed_ms(started),
                    retry_count=attempt,
                    excerpt=f"bytes={len(data)}",
                )
                return data, headers
            except WeKnoraUnavailableError as exc:
                last_error = exc
                if not exc.retryable or attempt >= attempts - 1:
                    _log_weknora_call(
                        request_id=request_id,
                        operation=safe_operation,
                        status="error",
                        status_code=exc.status_code,
                        duration_ms=_elapsed_ms(started),
                        retry_count=attempt,
                        error_code=exc.error_code,
                        excerpt=exc.message,
                    )
                    raise
                self._sleep_before_retry(attempt)
        if last_error is not None:
            raise last_error
        raise WeKnoraUnavailableError(
            "WeKnora binary request failed",
            operation=_sanitize_operation(operation),
            retryable=False,
        )

    def _read_response(self, request: Request, safe_operation: str) -> tuple[str, int | None]:
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                return response.read().decode("utf-8", errors="replace"), status_code
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise _http_error_to_weknora_error(exc.code, body_text, safe_operation) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise WeKnoraTimeoutError(
                "WeKnora request timed out",
                error_code="weknora_timeout",
                operation=safe_operation,
                retryable=True,
            ) from exc
        except URLError as exc:
            if _url_error_is_timeout(exc):
                raise WeKnoraTimeoutError(
                    "WeKnora request timed out",
                    error_code="weknora_timeout",
                    operation=safe_operation,
                    retryable=True,
                ) from exc
            raise WeKnoraNetworkError(
                "WeKnora network request failed",
                error_code="weknora_network_error",
                operation=safe_operation,
                retryable=True,
            ) from exc

    def _read_bytes_response(
        self,
        request: Request,
        safe_operation: str,
    ) -> tuple[bytes, dict[str, str], int | None]:
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                headers = {key.lower(): value for key, value in response.headers.items()}
                return response.read(), headers, status_code
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise _http_error_to_weknora_error(exc.code, body_text, safe_operation) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise WeKnoraTimeoutError(
                "WeKnora binary request timed out",
                error_code="weknora_timeout",
                operation=safe_operation,
                retryable=True,
            ) from exc
        except URLError as exc:
            if _url_error_is_timeout(exc):
                raise WeKnoraTimeoutError(
                    "WeKnora binary request timed out",
                    error_code="weknora_timeout",
                    operation=safe_operation,
                    retryable=True,
                ) from exc
            raise WeKnoraNetworkError(
                "WeKnora binary network request failed",
                error_code="weknora_network_error",
                operation=safe_operation,
                retryable=True,
            ) from exc

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_backoff_seconds <= 0:
            return
        delay = min(self.retry_backoff_seconds * (2 ** attempt), 2.0)
        time.sleep(delay)

    def _apply_auth_headers(self, headers: dict[str, str]) -> None:
        if not self.service_token:
            return
        headers["X-API-Key"] = self.service_token
        headers["Authorization"] = f"Bearer {self.service_token}"


class WeKnoraApiBackend(KnowledgeEngine):
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        workspace_id: str | None = None,
        default_kb_id: str | None = None,
        kb_mapping_config: str | None = None,
        kb_allow_default: bool | None = None,
        retry_attempts: int | None = None,
        retry_backoff_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("WEKNORA_BASE_URL", "")).rstrip("/")
        # WEKNORA_API_KEY is kept as a legacy fallback for older local .env files.
        self.service_token = (
            service_token
            if service_token is not None
            else api_key
            if api_key is not None
            else os.getenv("WEKNORA_SERVICE_TOKEN", os.getenv("WEKNORA_API_KEY", ""))
        )
        self.timeout = timeout if timeout is not None else _get_timeout_seconds(60.0)
        self.workspace_id = (
            workspace_id if workspace_id is not None else os.getenv("WEKNORA_WORKSPACE_ID", "")
        )
        self.default_kb_id = (
            default_kb_id if default_kb_id is not None else os.getenv("WEKNORA_DEFAULT_KB_ID", "")
        )
        self.kb_resolver = KbMappingResolver(
            default_workspace_id=self.workspace_id,
            default_kb_id=self.default_kb_id,
            mapping_config=kb_mapping_config,
            allow_default=kb_allow_default,
        )
        self.retry_attempts = (
            max(retry_attempts, 0)
            if retry_attempts is not None
            else _get_retry_attempts(1)
        )
        self.retry_backoff_seconds = (
            max(retry_backoff_seconds, 0.0)
            if retry_backoff_seconds is not None
            else _get_retry_backoff_seconds(0.25)
        )
        self.client = WeKnoraNativeClient(
            base_url=self.base_url,
            service_token=self.service_token,
            timeout=self.timeout,
            retry_attempts=self.retry_attempts,
            retry_backoff_seconds=self.retry_backoff_seconds,
        )

    @property
    def configured(self) -> bool:
        return self.client.configured

    def native_client_status(self) -> dict:
        return self.client.status(
            workspace_id=self.workspace_id,
            default_kb_id=self.default_kb_id,
        )

    def health(self) -> dict:
        if not self.configured:
            return {
                "status": "unavailable",
                "backend": "weknora_api",
                "configured": False,
                "source": "weknora_api",
                "native_client": self.native_client_status(),
            }
        try:
            data = self._request_json("GET", "/health")
        except KnowledgeBackendUnavailableError as exc:
            return {
                "status": "unavailable",
                "backend": "weknora_api",
                "configured": True,
                "source": "weknora_api",
                "error": str(exc),
                "native_client": self.native_client_status(),
            }
        if not isinstance(data, dict):
            data = {}
        return {
            "status": data.get("status", "ok"),
            "backend": "weknora_api",
            "configured": True,
            "source": "weknora_api",
            "native_client": self.native_client_status(),
        }

    def active_kb_target(self) -> dict:
        target = self.kb_resolver.resolve_one({}, operation="status")
        return {
            "workspace_id": target.workspace_id,
            "kb_id": target.kb_id,
            "mapping_name": target.mapping_name,
            "selection_source": target.selection_source,
            "default_used": target.default_used,
            "source": "weknora_api",
        }

    def get_workspace(self, workspace_id: str | None = None) -> dict:
        self._require_configured()
        resolved_workspace_id = str(workspace_id or self.workspace_id or "").strip()
        if not resolved_workspace_id:
            raise KnowledgeBackendUnavailableError("WEKNORA_WORKSPACE_ID is not configured")
        data = self._request_json(
            "GET",
            f"/api/v1/tenants/{quote(resolved_workspace_id, safe='')}",
        )
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora workspace returned invalid JSON")
        return {
            "id": _optional_str(payload.get("id")) or resolved_workspace_id,
            "name": _optional_str(payload.get("name") or payload.get("title")),
            "source": "weknora_api",
        }

    def get_knowledge_base(self, kb_id: str | None = None) -> dict:
        self._require_configured()
        resolved_kb_id = str(kb_id or self.default_kb_id or "").strip()
        if not resolved_kb_id:
            raise KnowledgeBackendUnavailableError("WEKNORA_DEFAULT_KB_ID is not configured")
        data = self._request_json(
            "GET",
            f"/api/v1/knowledge-bases/{quote(resolved_kb_id, safe='')}",
        )
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora knowledge base returned invalid JSON")
        return {
            "id": _optional_str(payload.get("id")) or resolved_kb_id,
            "name": _optional_str(payload.get("name") or payload.get("title")),
            "type": _optional_str(payload.get("type")),
            "is_temporary": bool(payload.get("is_temporary")),
            "knowledge_count": _optional_int(payload.get("knowledge_count")),
            "chunk_count": _optional_int(payload.get("chunk_count")),
            "is_processing": bool(payload.get("is_processing")),
            "vector_store": self._knowledge_base_vector_store_safe_dict(payload),
            "source": "weknora_api",
        }

    def list_knowledge_bases(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/knowledge-bases")
        payload = self._unwrap_data(data)
        items = _items_from_payload(payload)
        return [self._knowledge_base_safe_dict(item) for item in items if isinstance(item, dict)]

    def list_knowledge_base_tags(self, kb_id: str, *, limit: int = 20) -> list[dict]:
        self._require_configured()
        resolved_kb_id = str(kb_id or "").strip()
        if not resolved_kb_id:
            raise KnowledgeBackendUnavailableError("knowledge base id is required for tag list")
        safe_limit = max(min(int(limit or 20), 100), 1)
        data = self._request_json(
            "GET",
            "/api/v1/knowledge-bases/{kb_id}/tags?{query}".format(
                kb_id=quote(resolved_kb_id, safe=""),
                query=urlencode({"page": 1, "page_size": safe_limit}),
            ),
        )
        payload = self._unwrap_data(data)
        tags = _items_from_payload(payload)
        return [_knowledge_tag_safe_dict(tag) for tag in tags if isinstance(tag, dict)]

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        self._require_configured()
        target = self.kb_resolver.resolve_one(metadata, operation="upload_document")
        enriched_metadata = {**metadata, **target.metadata()}
        path = Path(file_path)
        fields = {
            "metadata": json.dumps(_string_metadata(enriched_metadata), ensure_ascii=False),
            "fileName": str(enriched_metadata.get("file_name") or path.name),
            "channel": str(enriched_metadata.get("weknora_channel") or "api"),
        }
        if enriched_metadata.get("tag_id"):
            fields["tag_id"] = str(enriched_metadata["tag_id"])
        if enriched_metadata.get("enable_multimodel") is not None:
            fields["enable_multimodel"] = _bool_string(enriched_metadata["enable_multimodel"])
        data = self._request_multipart_json(
            "/api/v1/knowledge-bases/{kb_id}/knowledge/file".format(
                kb_id=target.kb_id
            ),
            file_path=path,
            fields=fields,
        )
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora upload returned invalid JSON")
        external_doc_id = data.get("external_doc_id") or data.get("id")
        if not external_doc_id:
            raise KnowledgeBackendUnavailableError("WeKnora upload returned no document id")
        mapped_status = self._map_document_status(data.get("parse_status") or data.get("status"))
        return KnowledgeDocument(
            document_id=metadata.get("document_id"),
            external_doc_id=external_doc_id,
            title=data.get("title") or data.get("file_name") or metadata.get("title") or path.name,
            status=mapped_status,
            source="weknora_api",
            metadata=self._document_metadata(data, enriched_metadata),
        )

    def create_document_from_url(self, url: str, metadata: dict) -> KnowledgeDocument:
        self._require_configured()
        normalized_url = str(url or "").strip()
        if not normalized_url:
            raise KnowledgeBackendUnavailableError("document URL is required")
        target = self.kb_resolver.resolve_one(metadata, operation="create_document_from_url")
        enriched_metadata = {**metadata, **target.metadata()}
        payload = {
            "url": normalized_url,
            "title": str(enriched_metadata.get("title") or ""),
            "file_name": str(enriched_metadata.get("file_name") or ""),
            "file_type": str(enriched_metadata.get("file_type") or ""),
            "tag_id": str(enriched_metadata.get("tag_id") or ""),
            "channel": str(enriched_metadata.get("weknora_channel") or "pa_url"),
        }
        data = self._request_json(
            "POST",
            "/api/v1/knowledge-bases/{kb_id}/knowledge/url".format(kb_id=quote(target.kb_id, safe="")),
            {key: value for key, value in payload.items() if value not in (None, "")},
        )
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora URL ingestion returned invalid JSON")
        return self._to_knowledge_document(
            data=data,
            fallback_title=str(enriched_metadata.get("title") or normalized_url),
            original_metadata={**enriched_metadata, "weknora_ingestion_mode": "url"},
        )

    def create_manual_document(self, title: str, content: str, metadata: dict) -> KnowledgeDocument:
        self._require_configured()
        normalized_title = str(title or "").strip()
        normalized_content = str(content or "").strip()
        if not normalized_title:
            raise KnowledgeBackendUnavailableError("manual document title is required")
        if not normalized_content:
            raise KnowledgeBackendUnavailableError("manual document content is required")
        target = self.kb_resolver.resolve_one(metadata, operation="create_manual_document")
        enriched_metadata = {**metadata, **target.metadata()}
        payload = {
            "title": normalized_title,
            "content": normalized_content,
            "status": str(enriched_metadata.get("manual_status") or "publish"),
            "tag_id": str(enriched_metadata.get("tag_id") or ""),
            "channel": str(enriched_metadata.get("weknora_channel") or "pa_manual"),
        }
        data = self._request_json(
            "POST",
            "/api/v1/knowledge-bases/{kb_id}/knowledge/manual".format(kb_id=quote(target.kb_id, safe="")),
            {key: value for key, value in payload.items() if value not in (None, "")},
        )
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora manual ingestion returned invalid JSON")
        return self._to_knowledge_document(
            data=data,
            fallback_title=normalized_title,
            original_metadata={**enriched_metadata, "weknora_ingestion_mode": "manual"},
        )

    def get_document_status(self, external_doc_id: str) -> dict:
        self._require_configured()
        data = self._request_json("GET", f"/api/v1/knowledge/{external_doc_id}")
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            data = {}
        raw_status = data.get("parse_status") or data.get("status")
        mapped_status = self._map_document_status(raw_status)
        return {
            "external_doc_id": external_doc_id,
            "status": mapped_status,
            "source": "weknora_api",
            "message": self._status_message(data),
            "failed_step": self._document_failed_step(data, raw_status)
            if mapped_status == "failed"
            else None,
            "error_message": self._document_error_message(data),
            "metadata": self._document_metadata(data, {}),
        }

    def get_document_spans(self, external_doc_id: str) -> dict:
        self._require_configured()
        encoded_id = quote(str(external_doc_id or "").strip(), safe="")
        if not encoded_id:
            raise KnowledgeBackendUnavailableError("document id is required for spans")
        data = self._request_json("GET", f"/api/v1/knowledge/{encoded_id}/spans")
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora document spans returned invalid JSON")
        return {
            "source": "weknora_api",
            "external_doc_id": external_doc_id,
            "parse_status": _optional_str(payload.get("parse_status")),
            "current_attempt": _optional_int(payload.get("current_attempt")),
            "current_stage": _optional_str(payload.get("current_stage")),
            "trace": payload.get("trace") if isinstance(payload.get("trace"), dict) else {},
            "last_error": payload.get("last_error") if isinstance(payload.get("last_error"), dict) else None,
        }

    def reparse_document(self, external_doc_id: str) -> dict:
        self._require_configured()
        encoded_id = quote(str(external_doc_id or "").strip(), safe="")
        if not encoded_id:
            raise KnowledgeBackendUnavailableError("document id is required for reparse")
        data = self._request_json("POST", f"/api/v1/knowledge/{encoded_id}/reparse")
        return self._document_action_result(data, external_doc_id, action="reparse")

    def cancel_document_parse(self, external_doc_id: str) -> dict:
        self._require_configured()
        encoded_id = quote(str(external_doc_id or "").strip(), safe="")
        if not encoded_id:
            raise KnowledgeBackendUnavailableError("document id is required for cancel")
        data = self._request_json("POST", f"/api/v1/knowledge/{encoded_id}/cancel-parse")
        return self._document_action_result(data, external_doc_id, action="cancel_parse")

    def delete_document(self, external_doc_id: str) -> dict:
        self._require_configured()
        encoded_id = quote(str(external_doc_id or "").strip(), safe="")
        if not encoded_id:
            raise KnowledgeBackendUnavailableError("document id is required for delete")
        data = self._request_json("DELETE", f"/api/v1/knowledge/{encoded_id}")
        return self._document_action_result(data, external_doc_id, action="delete")

    def read_document_file(self, external_doc_id: str, *, preview: bool = False) -> dict:
        self._require_configured()
        encoded_id = quote(str(external_doc_id or "").strip(), safe="")
        if not encoded_id:
            raise KnowledgeBackendUnavailableError("document id is required for file read")
        suffix = "preview" if preview else "download"
        content, headers = self.client.request_bytes("GET", f"/api/v1/knowledge/{encoded_id}/{suffix}")
        return {
            "source": "weknora_api",
            "external_doc_id": external_doc_id,
            "content": content,
            "content_type": headers.get("content-type") or "application/octet-stream",
            "content_disposition": headers.get("content-disposition"),
            "content_length": len(content),
        }

    def list_document_chunks(
        self,
        external_doc_id: str,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        self._require_configured()
        query = urlencode(
            {
                "page": max(page, 1),
                "page_size": min(max(page_size, 1), 100),
                "chunk_type": "text",
            }
        )
        data = self._request_json("GET", f"/api/v1/chunks/{external_doc_id}?{query}")
        items = self._unwrap_items(data)
        return [
            self._to_document_chunk_preview(item, external_doc_id)
            for item in items
            if isinstance(item, dict)
        ]

    def get_document_chunk_by_id(self, chunk_id: str) -> dict:
        self._require_configured()
        encoded_id = quote(str(chunk_id or "").strip(), safe="")
        if not encoded_id:
            raise KnowledgeBackendUnavailableError("chunk id is required")
        data = self._request_json("GET", f"/api/v1/chunks/by-id/{encoded_id}")
        item = self._unwrap_data(data)
        if not isinstance(item, dict):
            raise WeKnoraResponseMappingError("WeKnora chunk response did not contain an object")
        external_doc_id = str(item.get("knowledge_id") or "")
        return self._to_document_chunk_preview(item, external_doc_id)

    def update_document_chunk(
        self,
        external_doc_id: str,
        chunk_id: str,
        *,
        content: str | None = None,
        is_enabled: bool,
    ) -> dict:
        self._require_configured()
        encoded_doc_id = quote(str(external_doc_id or "").strip(), safe="")
        encoded_chunk_id = quote(str(chunk_id or "").strip(), safe="")
        if not encoded_doc_id or not encoded_chunk_id:
            raise KnowledgeBackendUnavailableError("document id and chunk id are required")
        payload: dict[str, object] = {"is_enabled": is_enabled}
        if content is not None:
            payload["content"] = content
        data = self._request_json(
            "PUT",
            f"/api/v1/chunks/{encoded_doc_id}/{encoded_chunk_id}",
            payload,
        )
        item = self._unwrap_data(data)
        if not isinstance(item, dict):
            return self.get_document_chunk_by_id(chunk_id)
        return self._to_document_chunk_preview(item, external_doc_id)

    def delete_document_chunk(self, external_doc_id: str, chunk_id: str) -> dict:
        self._require_configured()
        encoded_doc_id = quote(str(external_doc_id or "").strip(), safe="")
        encoded_chunk_id = quote(str(chunk_id or "").strip(), safe="")
        if not encoded_doc_id or not encoded_chunk_id:
            raise KnowledgeBackendUnavailableError("document id and chunk id are required")
        data = self._request_json("DELETE", f"/api/v1/chunks/{encoded_doc_id}/{encoded_chunk_id}")
        return self._document_action_result(data, external_doc_id, action="delete_chunk")

    def delete_generated_question(self, chunk_id: str, question_id: str) -> dict:
        self._require_configured()
        encoded_chunk_id = quote(str(chunk_id or "").strip(), safe="")
        normalized_question_id = str(question_id or "").strip()
        if not encoded_chunk_id or not normalized_question_id:
            raise KnowledgeBackendUnavailableError("chunk id and question id are required")
        data = self._request_json(
            "DELETE",
            f"/api/v1/chunks/by-id/{encoded_chunk_id}/questions",
            {"question_id": normalized_question_id},
        )
        return self._document_action_result(data, chunk_id, action="delete_generated_question")

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        self._require_configured()
        normalized_query = query.strip()
        if not normalized_query:
            return []
        filters = filters or {}
        source_type_filter = self._normalized_source_type(filters.get("source_type"))
        if source_type_filter == "wiki_page":
            return self._retrieve_wiki_evidence(normalized_query, filters, top_k)
        payload = self._retrieve_payload(normalized_query, filters)
        data = self._request_json("POST", "/api/v1/knowledge-search", payload)
        items = self._unwrap_items(data)
        retrieval_metadata = self._retrieval_metadata(filters)
        knowledge_scope = _knowledge_scope_filter(filters)
        evidence_items = [
            self._to_evidence(item, retrieval_metadata, native_rank=native_rank)
            for native_rank, item in enumerate(items, start=1)
            if isinstance(item, dict)
        ]
        if knowledge_scope:
            evidence_items = [
                evidence
                for evidence in evidence_items
                if evidence.external_doc_id in knowledge_scope
            ]
        if source_type_filter:
            evidence_items = [
                evidence
                for evidence in evidence_items
                if evidence.source_type == source_type_filter
            ]
            return evidence_items[: max(top_k, 0)]

        wiki_items = self._retrieve_wiki_evidence(normalized_query, filters, top_k)
        return _interleave_evidence_sources(evidence_items, wiki_items)[: max(top_k, 0)]

    def _retrieve_wiki_evidence(
        self,
        query: str,
        filters: dict,
        top_k: int,
    ) -> list[Evidence]:
        if top_k <= 0:
            return []
        targets = self.kb_resolver.resolve_many(filters, operation="wiki_retrieve")

        evidence_items: list[Evidence] = []
        query_variants = _wiki_retrieval_queries(query, filters)
        seen: set[str] = set()
        limit = max(top_k, 1)
        for target in targets:
            kb_id = target.kb_id
            for variant_index, wiki_query in enumerate(query_variants, start=1):
                summaries = self.search_wiki(wiki_query, kb_id=kb_id, limit=limit)
                for summary in summaries:
                    page = self.read_wiki_page(summary.slug, kb_id=kb_id)
                    if page is None:
                        page = WikiPage(
                            slug=summary.slug,
                            title=summary.title,
                            page_type=summary.page_type,
                            summary=summary.summary,
                            content=summary.summary,
                            citations=[],
                            source="weknora_api",
                            metadata=summary.metadata,
                        )
                    evidence = self._wiki_page_to_evidence(page, kb_id)
                    key = evidence.evidence_id or evidence.wiki_page_id or summary.slug
                    if key in seen:
                        continue
                    seen.add(key)
                    evidence_items.append(
                        replace(
                            evidence,
                            metadata={
                                **evidence.metadata,
                                "wiki_search_original_query": query,
                                "wiki_search_query": wiki_query,
                                "wiki_search_query_variant_index": variant_index,
                                "wiki_search_query_variant_count": len(query_variants),
                                "wiki_search_query_variants": query_variants,
                            },
                        )
                    )
                    if len(evidence_items) >= max(top_k, 0):
                        return evidence_items
        return evidence_items[: max(top_k, 0)]

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        query_params = {"q": query, "limit": max(limit, 1)}
        data = self._request_json(
            "GET",
            f"{self._wiki_base_path(resolved_kb_id)}/search?{urlencode(query_params)}",
        )
        items = self._unwrap_wiki_pages(data)
        return [
            self._to_wiki_page_summary(item)
            for item in items
            if isinstance(item, dict)
        ]

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        encoded_slug = quote(slug.strip(), safe="/")
        data = self._request_json(
            "GET",
            f"{self._wiki_base_path(resolved_kb_id)}/pages/{encoded_slug}",
        )
        data = self._unwrap_data(data)
        if not data or not isinstance(data, dict):
            return None
        return self._to_wiki_page(data, slug)

    def create_wiki_page(
        self,
        page: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        payload = self._wiki_page_payload(page)
        data = self._request_json(
            "POST",
            f"{self._wiki_base_path(resolved_kb_id)}/pages",
            payload,
        )
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora Wiki create returned invalid JSON")
        return self._to_wiki_page(data, str(payload.get("slug") or ""))

    def update_wiki_page(
        self,
        slug: str,
        page: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        payload = self._wiki_page_payload({**page, "slug": slug})
        encoded_slug = quote(slug.strip(), safe="/")
        data = self._request_json(
            "PUT",
            f"{self._wiki_base_path(resolved_kb_id)}/pages/{encoded_slug}",
            payload,
        )
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora Wiki update returned invalid JSON")
        return self._to_wiki_page(data, slug)

    def list_wiki_pages(
        self,
        kb_id: str | None = None,
        *,
        query: str = "",
        page_type: str = "",
        status: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        params: dict[str, object] = {
            "page": max(page, 1),
            "page_size": max(page_size, 1),
            "sort_by": "updated_at",
            "sort_order": "desc",
        }
        if query:
            params["query"] = query
        if page_type:
            params["page_type"] = page_type
        if status:
            params["status"] = status
        data = self._request_json(
            "GET",
            f"{self._wiki_base_path(resolved_kb_id)}/pages?{urlencode(params)}",
        )
        payload = self._unwrap_data(data)
        pages = self._unwrap_wiki_pages(data)
        return {
            "pages": [self._wiki_summary_dict(item) for item in pages if isinstance(item, dict)],
            "total": _optional_int(payload.get("total")) if isinstance(payload, dict) else None,
            "page": _optional_int(payload.get("page")) if isinstance(payload, dict) else None,
            "page_size": _optional_int(payload.get("page_size")) if isinstance(payload, dict) else None,
            "total_pages": _optional_int(payload.get("total_pages")) if isinstance(payload, dict) else None,
            "source": "weknora_api",
            "kb_id": resolved_kb_id,
        }

    def get_wiki_index(
        self,
        kb_id: str | None = None,
        *,
        page_types: list[str] | None = None,
        limit: int = 20,
        cursor: str = "",
    ) -> dict:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        params: dict[str, object] = {"limit": max(limit, 1)}
        if page_types:
            params["types"] = ",".join(page_types)
        if cursor:
            params["cursor"] = cursor
        data = self._request_json(
            "GET",
            f"{self._wiki_base_path(resolved_kb_id)}/index?{urlencode(params)}",
        )
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora Wiki index returned invalid JSON")
        groups = []
        for group in payload.get("groups") or []:
            if not isinstance(group, dict):
                continue
            items = [
                self._wiki_index_entry_dict(item)
                for item in group.get("items") or []
                if isinstance(item, dict)
            ]
            groups.append(
                {
                    "type": _optional_str(group.get("type")) or "unknown",
                    "total": _optional_int(group.get("total")) or 0,
                    "items": items,
                    "next_cursor": _optional_str(group.get("next_cursor")),
                }
            )
        return {
            "intro_present": bool(str(payload.get("intro") or "").strip()),
            "version": _optional_int(payload.get("version")),
            "groups": groups,
            "source": "weknora_api",
            "kb_id": resolved_kb_id,
        }

    def get_wiki_stats(self, kb_id: str | None = None) -> dict:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        data = self._request_json("GET", f"{self._wiki_base_path(resolved_kb_id)}/stats")
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora Wiki stats returned invalid JSON")
        return {
            "total_pages": _optional_int(payload.get("total_pages")) or 0,
            "pages_by_type": _int_mapping(payload.get("pages_by_type")),
            "total_links": _optional_int(payload.get("total_links")) or 0,
            "orphan_count": _optional_int(payload.get("orphan_count")) or 0,
            "pending_tasks": _optional_int(payload.get("pending_tasks")) or 0,
            "pending_issues": _optional_int(payload.get("pending_issues")) or 0,
            "is_active": bool(payload.get("is_active")),
            "recent_updates": [
                self._wiki_summary_dict(item)
                for item in payload.get("recent_updates") or []
                if isinstance(item, dict)
            ],
            "source": "weknora_api",
            "kb_id": resolved_kb_id,
        }

    def get_wiki_graph(
        self,
        kb_id: str | None = None,
        *,
        mode: str = "overview",
        center: str = "",
        depth: int = 1,
        page_types: list[str] | None = None,
        limit: int = 50,
    ) -> dict:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        params: dict[str, object] = {
            "mode": mode,
            "depth": max(depth, 1),
            "limit": max(limit, 1),
        }
        if center:
            params["center"] = center
        if page_types:
            params["types"] = ",".join(page_types)
        data = self._request_json(
            "GET",
            f"{self._wiki_base_path(resolved_kb_id)}/graph?{urlencode(params)}",
        )
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora Wiki graph returned invalid JSON")
        nodes = [item for item in payload.get("nodes") or [] if isinstance(item, dict)]
        edges = [item for item in payload.get("edges") or [] if isinstance(item, dict)]
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        return {
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "sample_nodes": [
                {
                    "slug": _optional_str(item.get("slug")),
                    "title": _optional_str(item.get("title")),
                    "page_type": _optional_str(item.get("page_type")),
                    "link_count": _optional_int(item.get("link_count")) or 0,
                }
                for item in nodes[:5]
            ],
            "meta": {
                "mode": _optional_str(meta.get("mode")) or mode,
                "total": _optional_int(meta.get("total")) or 0,
                "returned": _optional_int(meta.get("returned")) or len(nodes),
                "truncated": bool(meta.get("truncated")),
                "center": _optional_str(meta.get("center")),
                "depth": _optional_int(meta.get("depth")),
            },
            "source": "weknora_api",
            "kb_id": resolved_kb_id,
        }

    def get_wiki_lint(self, kb_id: str | None = None) -> dict:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        data = self._request_json("GET", f"{self._wiki_base_path(resolved_kb_id)}/lint")
        payload = self._unwrap_data(data)
        if not isinstance(payload, dict):
            raise KnowledgeBackendUnavailableError("WeKnora Wiki lint returned invalid JSON")
        issues = [item for item in payload.get("issues") or [] if isinstance(item, dict)]
        return {
            "health_score": _optional_int(payload.get("health_score")),
            "issue_count": len(issues),
            "summary": _shorten(str(payload.get("summary") or ""), 240),
            "sample_issues": [
                {
                    "type": _optional_str(item.get("type")),
                    "severity": _optional_str(item.get("severity")),
                    "page_slug": _optional_str(item.get("page_slug")),
                    "fixable": bool(item.get("fixable")),
                }
                for item in issues[:5]
            ],
            "source": "weknora_api",
            "kb_id": resolved_kb_id,
        }

    def list_wiki_issues(
        self,
        kb_id: str | None = None,
        *,
        slug: str = "",
        status: str = "",
    ) -> list[dict]:
        self._require_configured()
        resolved_kb_id = self._wiki_kb_id(kb_id)
        params: dict[str, str] = {}
        if slug:
            params["slug"] = slug
        if status:
            params["status"] = status
        suffix = f"?{urlencode(params)}" if params else ""
        data = self._request_json(
            "GET",
            f"{self._wiki_base_path(resolved_kb_id)}/issues{suffix}",
        )
        items = self._unwrap_items(data)
        return [
            {
                "id": _optional_str(item.get("id")),
                "slug": _optional_str(item.get("slug")),
                "issue_type": _optional_str(item.get("issue_type")),
                "status": _optional_str(item.get("status")),
                "reported_by": _optional_str(item.get("reported_by")),
            }
            for item in items
            if isinstance(item, dict)
        ]

    def list_agents(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/agents")
        items = self._unwrap_items(data)
        return [item for item in items if isinstance(item, dict)]

    def list_agent_type_presets(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/agents/type-presets")
        payload = self._unwrap_data(data)
        items = _items_from_payload(payload)
        return [item for item in items if isinstance(item, dict)]

    def list_agent_placeholders(self) -> dict:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/agents/placeholders")
        payload = self._unwrap_data(data)
        return payload if isinstance(payload, dict) else {}

    def get_agent_suggested_questions(
        self,
        *,
        agent_id: str,
        knowledge_base_ids: list[str] | None = None,
        knowledge_ids: list[str] | None = None,
        limit: int = 6,
    ) -> list[dict]:
        self._require_configured()
        normalized_agent_id = str(agent_id or "").strip()
        if not normalized_agent_id:
            raise KnowledgeBackendUnavailableError("agent id is required")
        params = {
            "limit": max(min(int(limit or 6), 20), 1),
        }
        if knowledge_base_ids:
            params["knowledge_base_ids"] = ",".join(str(item) for item in knowledge_base_ids if item)
        if knowledge_ids:
            params["knowledge_ids"] = ",".join(str(item) for item in knowledge_ids if item)
        data = self._request_json(
            "GET",
            "/api/v1/agents/{agent_id}/suggested-questions?{query}".format(
                agent_id=quote(normalized_agent_id, safe=""),
                query=urlencode(params),
            ),
        )
        payload = self._unwrap_data(data)
        if isinstance(payload, dict):
            questions = payload.get("questions")
        else:
            questions = payload
        items = questions if isinstance(questions, list) else []
        return [item for item in items if isinstance(item, dict)]

    def list_mcp_services(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/mcp-services")
        items = self._unwrap_items(data)
        return [
            self._mcp_service_safe_dict(item)
            for item in items
            if isinstance(item, dict)
        ]

    def get_mcp_service_tools(self, service_id: str) -> list[dict]:
        self._require_configured()
        encoded_id = quote(service_id, safe="")
        data = self._request_json("GET", f"/api/v1/mcp-services/{encoded_id}/tools")
        items = self._unwrap_items(data)
        return [
            {
                "name": _optional_str(item.get("name")),
                "require_approval": bool(item.get("require_approval")),
            }
            for item in items
            if isinstance(item, dict)
        ]

    def get_mcp_service_resources(self, service_id: str) -> list[dict]:
        self._require_configured()
        encoded_id = quote(service_id, safe="")
        data = self._request_json("GET", f"/api/v1/mcp-services/{encoded_id}/resources")
        items = self._unwrap_items(data)
        return [
            {
                "name": _optional_str(item.get("name")),
                "mime_type": _optional_str(item.get("mimeType") or item.get("mime_type")),
            }
            for item in items
            if isinstance(item, dict)
        ]

    def list_mcp_tool_approvals(self, service_id: str) -> list[dict]:
        self._require_configured()
        encoded_id = quote(service_id, safe="")
        data = self._request_json(
            "GET",
            f"/api/v1/mcp-services/{encoded_id}/tool-approvals",
        )
        items = self._unwrap_items(data)
        return [
            {
                "tool_name": _optional_str(item.get("tool_name")),
                "require_approval": bool(item.get("require_approval")),
            }
            for item in items
            if isinstance(item, dict)
        ]

    def list_web_search_provider_types(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/web-search-providers/types")
        items = self._unwrap_items(data)
        return [
            self._web_search_provider_type_safe_dict(item)
            for item in items
            if isinstance(item, dict)
        ]

    def list_web_search_providers(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/web-search-providers")
        items = self._unwrap_items(data)
        return [
            self._web_search_provider_safe_dict(item)
            for item in items
            if isinstance(item, dict)
        ]

    def list_vector_store_types(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/vector-stores/types")
        items = self._unwrap_items(data)
        return [
            self._vector_store_type_safe_dict(item)
            for item in items
            if isinstance(item, dict)
        ]

    def list_vector_stores(self) -> list[dict]:
        self._require_configured()
        data = self._request_json("GET", "/api/v1/vector-stores")
        items = self._unwrap_items(data)
        return [
            self._vector_store_safe_dict(item)
            for item in items
            if isinstance(item, dict)
        ]

    def create_agent_session(
        self,
        title: str,
        description: str | None = None,
    ) -> str:
        self._require_configured()
        payload = {"title": title, "description": description or ""}
        data = self._request_json("POST", "/api/v1/sessions", payload)
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora session create returned invalid JSON")
        session_id = _optional_str(data.get("id"))
        if not session_id:
            raise KnowledgeBackendUnavailableError("WeKnora session create returned no session id")
        return session_id

    def run_agent_qa(
        self,
        *,
        session_id: str,
        query: str,
        agent_id: str,
        knowledge_base_ids: list[str] | None = None,
        knowledge_ids: list[str] | None = None,
        web_search_enabled: bool = False,
        disable_title: bool = True,
    ) -> dict:
        self._require_configured()
        payload = {
            "query": query,
            "agent_enabled": True,
            "agent_id": agent_id,
            "knowledge_base_ids": knowledge_base_ids or [],
            "knowledge_ids": knowledge_ids or [],
            "web_search_enabled": web_search_enabled,
            "disable_title": disable_title,
        }
        events = self._request_sse_json(
            "POST",
            f"/api/v1/agent-chat/{quote(session_id, safe='')}",
            payload,
        )
        answer_parts: list[str] = []
        reference_items: list[dict] = []
        event_counts: dict[str, int] = {}
        errors: list[str] = []
        tool_names: list[str] = []
        for event_item in events:
            response_type = str(event_item.get("response_type") or "unknown")
            event_counts[response_type] = event_counts.get(response_type, 0) + 1
            if response_type == "answer":
                answer_parts.append(str(event_item.get("content") or ""))
            elif response_type == "references":
                references = event_item.get("knowledge_references")
                if isinstance(references, list):
                    reference_items.extend(
                        item for item in references if isinstance(item, dict)
                    )
            elif response_type == "tool_call":
                data = event_item.get("data")
                if isinstance(data, dict):
                    tool_name = _optional_str(data.get("tool_name"))
                    if tool_name and tool_name not in tool_names:
                        tool_names.append(tool_name)
            elif response_type == "error":
                error_text = _optional_str(event_item.get("content"))
                if error_text:
                    errors.append(_shorten(_redact_sensitive_text(error_text), 240))

        evidence_items = [
            self._to_evidence(
                item,
                {
                    "weknora_agentqa_native": True,
                    "weknora_agentqa_agent_id": agent_id,
                    "weknora_agentqa_session_id": session_id,
                    "weknora_agentqa_event_source": "references",
                },
                native_rank=native_rank,
            )
            for native_rank, item in enumerate(reference_items, start=1)
        ]
        return {
            "session_id": session_id,
            "agent_id": agent_id,
            "answer": "".join(answer_parts),
            "evidence_items": evidence_items,
            "event_counts": event_counts,
            "errors": errors,
            "tool_names": tool_names,
            "reference_count": len(reference_items),
        }

    def run_knowledge_chat(
        self,
        *,
        session_id: str,
        query: str,
        knowledge_base_ids: list[str] | None = None,
        knowledge_ids: list[str] | None = None,
        web_search_enabled: bool = False,
        disable_title: bool = True,
    ) -> dict:
        self._require_configured()
        payload = {
            "query": query,
            "knowledge_base_ids": knowledge_base_ids or [],
            "knowledge_ids": knowledge_ids or [],
            "web_search_enabled": web_search_enabled,
            "disable_title": disable_title,
        }
        events = self._request_sse_json(
            "POST",
            f"/api/v1/knowledge-chat/{quote(session_id, safe='')}",
            payload,
        )
        answer_parts: list[str] = []
        reference_items: list[dict] = []
        event_counts: dict[str, int] = {}
        errors: list[str] = []
        for event_item in events:
            response_type = str(event_item.get("response_type") or "unknown")
            event_counts[response_type] = event_counts.get(response_type, 0) + 1
            if response_type == "answer":
                answer_parts.append(str(event_item.get("content") or ""))
            elif response_type == "references":
                references = event_item.get("knowledge_references")
                if isinstance(references, list):
                    reference_items.extend(
                        item for item in references if isinstance(item, dict)
                    )
            elif response_type == "error":
                error_text = _optional_str(event_item.get("content"))
                if error_text:
                    errors.append(_shorten(_redact_sensitive_text(error_text), 240))

        evidence_items = [
            self._to_evidence(
                item,
                {
                    "weknora_knowledge_chat_native": True,
                    "weknora_knowledge_chat_session_id": session_id,
                    "weknora_knowledge_chat_event_source": "references",
                },
                native_rank=native_rank,
            )
            for native_rank, item in enumerate(reference_items, start=1)
        ]
        return {
            "session_id": session_id,
            "answer": "".join(answer_parts),
            "evidence_items": evidence_items,
            "event_counts": event_counts,
            "errors": errors,
            "reference_count": len(reference_items),
        }

    def _request_json(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        return self.client.request_json(method, path, payload)

    def _request_multipart_json(
        self,
        path: str,
        file_path: Path,
        fields: dict[str, str],
    ) -> dict | list:
        return self.client.request_multipart_json(path, file_path, fields)

    def _request_sse_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> list[dict]:
        return self.client.request_sse_json(method, path, payload)

    def _perform_json_request(self, request: Request, operation: str) -> dict | list:
        return self.client._perform_json_request(request, operation)

    def _read_response(self, request: Request, safe_operation: str) -> tuple[str, int | None]:
        return self.client._read_response(request, safe_operation)

    def _sleep_before_retry(self, attempt: int) -> None:
        self.client._sleep_before_retry(attempt)

    def _require_configured(self) -> None:
        if not self.configured:
            raise KnowledgeBackendUnavailableError("WEKNORA_BASE_URL is not configured")

    def _apply_auth_headers(self, headers: dict[str, str]) -> None:
        self.client._apply_auth_headers(headers)

    @staticmethod
    def _unwrap_data(value: dict | list) -> dict | list:
        if isinstance(value, dict) and "data" in value and value.get("success") is not False:
            data = value.get("data")
            if isinstance(data, (dict, list)):
                return data
        return value

    @staticmethod
    def _map_document_status(raw_status: object) -> str:
        normalized = str(raw_status or "").strip().lower()
        if normalized in {"created", "pending", "uploaded"}:
            return "uploaded"
        if normalized in {"parsing", "processing"}:
            return "parsing"
        if normalized in {"chunking", "splitting"}:
            return "chunking"
        if normalized in {"embedding", "indexing", "finalizing"}:
            return "indexing"
        if normalized in {"completed", "indexed", "ready"}:
            return "indexed"
        if normalized in {
            "failed",
            "error",
            "cancelled",
            "parse_failed",
            "parsing_failed",
            "chunk_failed",
            "chunking_failed",
            "embedding_failed",
            "index_failed",
            "indexing_failed",
            "upload_failed",
        }:
            return "failed"
        return "unknown"

    @staticmethod
    def _document_failed_step(data: dict, raw_status: object) -> str:
        explicit_step = data.get("failed_step") or data.get("failedStep") or data.get("step")
        normalized_step = str(explicit_step or "").strip().lower()
        if normalized_step in {"parse", "parsing"}:
            return "parse"
        if normalized_step in {"chunk", "chunking", "split", "splitting"}:
            return "chunk"
        if normalized_step in {"embedding", "embed"}:
            return "embedding"
        if normalized_step in {"index", "indexing", "finalizing"}:
            return "index"
        if normalized_step in {"upload", "weknora_upload"}:
            return "weknora_upload"

        normalized_status = str(raw_status or "").strip().lower()
        if "parse" in normalized_status:
            return "parse"
        if "chunk" in normalized_status or "split" in normalized_status:
            return "chunk"
        if "embedding" in normalized_status or "embed" in normalized_status:
            return "embedding"
        if "index" in normalized_status:
            return "index"
        if "upload" in normalized_status:
            return "weknora_upload"
        return "weknora"

    @staticmethod
    def _document_metadata(data: dict, original_metadata: dict) -> dict:
        metadata = dict(original_metadata)
        raw_metadata = data.get("metadata")
        if isinstance(raw_metadata, dict):
            metadata.update(raw_metadata)
        for key in (
            "id",
            "knowledge_base_id",
            "tag_id",
            "type",
            "source",
            "channel",
            "parse_status",
            "pending_subtasks_count",
            "summary_status",
            "enable_status",
            "embedding_model_id",
            "file_name",
            "file_type",
            "file_size",
            "file_hash",
            "storage_size",
            "processed_at",
            "error_message",
        ):
            if key in data and data.get(key) not in (None, ""):
                metadata[f"weknora_{key}"] = data.get(key)
        metadata["source"] = "weknora_api"
        return metadata

    def _to_knowledge_document(
        self,
        *,
        data: dict,
        fallback_title: str,
        original_metadata: dict,
    ) -> KnowledgeDocument:
        external_doc_id = data.get("external_doc_id") or data.get("id")
        if not external_doc_id:
            raise KnowledgeBackendUnavailableError("WeKnora ingestion returned no document id")
        return KnowledgeDocument(
            document_id=original_metadata.get("document_id"),
            external_doc_id=external_doc_id,
            title=data.get("title") or data.get("file_name") or fallback_title,
            status=self._map_document_status(data.get("parse_status") or data.get("status")),
            source="weknora_api",
            metadata=self._document_metadata(data, original_metadata),
        )

    def _document_action_result(self, data: dict | list, external_doc_id: str, action: str) -> dict:
        payload = self._unwrap_data(data)
        payload = payload if isinstance(payload, dict) else {}
        raw_status = payload.get("parse_status") or payload.get("status")
        return {
            "source": "weknora_api",
            "action": action,
            "external_doc_id": external_doc_id,
            "status": self._map_document_status(raw_status),
            "native_status": _optional_str(raw_status),
            "task_id": _optional_str(payload.get("task_id")),
            "message": _shorten(str(payload.get("message") or payload.get("status") or action), 240),
            "metadata": self._document_metadata(payload, {}),
        }

    @staticmethod
    def _status_message(data: dict) -> str | None:
        raw_status = data.get("parse_status") or data.get("status")
        if not raw_status:
            return None
        message = f"WeKnora document status: {raw_status}"
        pending = data.get("pending_subtasks_count")
        if pending not in (None, "", 0):
            message = f"{message}; pending subtasks: {pending}"
        return message

    @staticmethod
    def _document_error_message(data: dict) -> str | None:
        for key in ("error_message", "error", "message", "reason", "failed_reason"):
            value = data.get(key)
            if value in (None, ""):
                continue
            if isinstance(value, dict):
                message = value.get("message") or value.get("detail") or value.get("code")
                if message:
                    return _shorten(_redact_sensitive_text(str(message)), 300)
                return _shorten(_redact_sensitive_text(json.dumps(value, default=str)), 300)
            return _shorten(_redact_sensitive_text(str(value)), 300)
        return None

    @staticmethod
    def _mcp_service_safe_dict(item: dict) -> dict:
        credentials = item.get("credentials")
        credential_field_count = 0
        configured_credential_field_count = 0
        if isinstance(credentials, dict):
            for field in credentials.values():
                if isinstance(field, dict):
                    credential_field_count += 1
                    if field.get("configured"):
                        configured_credential_field_count += 1
        return {
            "id": _optional_str(item.get("id")),
            "name": _optional_str(item.get("name")),
            "enabled": bool(item.get("enabled")),
            "transport_type": _optional_str(item.get("transport_type")),
            "is_builtin": bool(item.get("is_builtin")),
            "credential_field_count": credential_field_count,
            "configured_credential_field_count": configured_credential_field_count,
            "credentials_configured": configured_credential_field_count > 0,
            "source": "weknora_api",
        }

    @staticmethod
    def _web_search_provider_type_safe_dict(item: dict) -> dict:
        return {
            "id": _optional_str(item.get("id")),
            "name": _optional_str(item.get("name")),
            "requires_api_key": bool(item.get("requires_api_key")),
            "requires_engine_id": bool(item.get("requires_engine_id")),
            "requires_base_url": bool(item.get("requires_base_url")),
            "supports_proxy": bool(item.get("supports_proxy")),
            "source": "weknora_api",
        }

    @staticmethod
    def _web_search_provider_safe_dict(item: dict) -> dict:
        credentials = item.get("credentials")
        credential_field_count = 0
        configured_credential_field_count = 0
        if isinstance(credentials, dict):
            for field in credentials.values():
                if isinstance(field, dict):
                    credential_field_count += 1
                    if field.get("configured"):
                        configured_credential_field_count += 1
        return {
            "id": _optional_str(item.get("id")),
            "provider": _optional_str(item.get("provider")),
            "is_default": bool(item.get("is_default")),
            "credential_field_count": credential_field_count,
            "configured_credential_field_count": configured_credential_field_count,
            "credentials_configured": configured_credential_field_count > 0,
            "source": "weknora_api",
        }

    @staticmethod
    def _vector_store_type_safe_dict(item: dict) -> dict:
        connection_fields = item.get("connection_fields")
        index_fields = item.get("index_fields")
        safe_connection_fields = connection_fields if isinstance(connection_fields, list) else []
        safe_index_fields = index_fields if isinstance(index_fields, list) else []
        return {
            "type": _optional_str(item.get("type")),
            "display_name": _optional_str(item.get("display_name")),
            "connection_field_count": len(safe_connection_fields),
            "sensitive_connection_field_count": sum(
                1
                for field in safe_connection_fields
                if isinstance(field, dict) and bool(field.get("sensitive"))
            ),
            "index_field_count": len(safe_index_fields),
            "source": "weknora_api",
        }

    @staticmethod
    def _vector_store_safe_dict(item: dict) -> dict:
        return {
            "engine_type": _optional_str(item.get("engine_type")),
            "source": _optional_str(item.get("source")) or "weknora_api",
            "readonly": bool(item.get("readonly")),
            "status": _optional_str(item.get("status")) or "available",
        }

    @staticmethod
    def _knowledge_base_vector_store_safe_dict(item: dict) -> dict:
        source = _optional_str(item.get("vector_store_source"))
        status = _optional_str(item.get("vector_store_status"))
        engine_type = _optional_str(item.get("vector_store_engine_type"))
        return {
            "bound": bool(item.get("vector_store_id")),
            "source": source,
            "status": status,
            "engine_type": engine_type,
            "available": status == "available",
        }

    def _knowledge_base_safe_dict(self, item: dict) -> dict:
        return {
            "id": _optional_str(item.get("id")),
            "name": _optional_str(item.get("name") or item.get("title")),
            "description": _optional_str(item.get("description")),
            "type": _optional_str(item.get("type")),
            "is_temporary": bool(item.get("is_temporary")),
            "knowledge_count": _optional_int(item.get("knowledge_count")),
            "chunk_count": _optional_int(item.get("chunk_count")),
            "processing_count": _optional_int(item.get("processing_count")),
            "share_count": _optional_int(item.get("share_count")),
            "is_processing": bool(item.get("is_processing")),
            "is_pinned": bool(item.get("is_pinned")),
            "creator_name": _optional_str(item.get("creator_name")),
            "my_permission": _optional_str(item.get("my_permission")),
            "vector_store": self._knowledge_base_vector_store_safe_dict(item),
            "source": "weknora_api",
        }

    def _retrieve_payload(self, query: str, filters: dict) -> dict:
        payload: dict[str, object] = {"query": query}
        knowledge_ids = _knowledge_scope_filter(filters)
        if knowledge_ids:
            payload["knowledge_ids"] = knowledge_ids
        else:
            targets = self.kb_resolver.resolve_many(filters, operation="retrieve")
            payload["knowledge_base_ids"] = [target.kb_id for target in targets]
        options = normalize_retrieval_options(filters.get(RETRIEVAL_OPTIONS_KEY))
        options_payload = retrieval_options_payload(options)
        if options_payload:
            payload[RETRIEVAL_OPTIONS_KEY] = options_payload
        return payload

    def _wiki_kb_id(self, kb_id: str | None = None) -> str:
        return self.kb_resolver.resolve_one(
            {"kb_id": kb_id} if kb_id else {},
            operation="wiki",
        ).kb_id

    @staticmethod
    def _wiki_base_path(kb_id: str) -> str:
        return f"/api/v1/knowledgebase/{quote(kb_id, safe='')}/wiki"

    @staticmethod
    def _wiki_page_payload(page: dict) -> dict:
        page_metadata = page.get("page_metadata")
        metadata = dict(page_metadata) if isinstance(page_metadata, dict) else {}
        extra_metadata = page.get("metadata")
        if isinstance(extra_metadata, dict):
            metadata.update(extra_metadata)
        payload = {
            "slug": str(page.get("slug") or "").strip(),
            "title": str(page.get("title") or "Untitled").strip() or "Untitled",
            "page_type": str(page.get("page_type") or page.get("type") or "wiki"),
            "status": str(page.get("status") or "draft"),
            "content": str(page.get("content") or page.get("content_markdown") or ""),
            "summary": str(page.get("summary") or ""),
            "page_metadata": metadata,
        }
        for key in ("aliases", "source_refs", "chunk_refs", "in_links", "out_links"):
            value = page.get(key)
            if isinstance(value, list):
                payload[key] = value
        return payload

    @staticmethod
    def _unwrap_items(value: dict | list) -> list:
        data = WeKnoraApiBackend._unwrap_data(value)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "results", "data"):
                items = data.get(key)
                if isinstance(items, list):
                    return items
        return []

    @staticmethod
    def _unwrap_wiki_pages(value: dict | list) -> list:
        data = WeKnoraApiBackend._unwrap_data(value)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("pages", "items", "results", "data"):
                items = data.get(key)
                if isinstance(items, list):
                    return items
        return []

    @staticmethod
    def _retrieval_metadata(filters: dict) -> dict:
        options = normalize_retrieval_options(filters.get(RETRIEVAL_OPTIONS_KEY))
        options_payload = retrieval_options_payload(options)
        return {
            "retrieval_options": options,
            "retrieval_debug_trace": retrieval_debug_trace(options),
            "weknora_retrieval_options_forwarded": bool(options_payload),
            "weknora_search_endpoint": "/api/v1/knowledge-search",
            "weknora_search_native": True,
        }

    @staticmethod
    def _to_evidence(
        item: dict,
        retrieval_metadata: dict | None = None,
        native_rank: int | None = None,
    ) -> Evidence:
        metadata = WeKnoraApiBackend._search_result_metadata(item)
        if retrieval_metadata:
            metadata.update(retrieval_metadata)
        if native_rank is not None:
            metadata["weknora_native_rank"] = native_rank
        source_type = WeKnoraApiBackend._source_type(item, metadata)
        chunk_id = None if source_type == "wiki_page" else item.get("chunk_id") or item.get("id")
        wiki_page_id = (
            item.get("wiki_page_id")
            or item.get("wiki_id")
            or item.get("wiki_page_slug")
            or item.get("slug")
            or item.get("page_id")
            or metadata.get("weknora_slug")
        )
        evidence_id = (
            item.get("evidence_id")
            or metadata.get("evidence_id")
            or WeKnoraApiBackend._evidence_id(source_type, chunk_id, wiki_page_id)
        )
        metadata.setdefault("evidence_id", evidence_id)
        metadata.setdefault("citation_source_type", source_type)
        return Evidence(
            document_id=item.get("document_id"),
            external_doc_id=(
                item.get("external_doc_id")
                or item.get("doc_id")
                or item.get("knowledge_id")
            ),
            chunk_id=chunk_id,
            title=(
                item.get("title")
                or item.get("wiki_title")
                or item.get("page_title")
                or item.get("knowledge_title")
                or item.get("knowledge_filename")
                or "Untitled evidence"
            ),
            text=item.get("text") or item.get("content") or item.get("matched_content") or "",
            score=item.get("score"),
            source="weknora_api",
            metadata=metadata,
            evidence_id=evidence_id,
            source_type=source_type,
            wiki_page_id=wiki_page_id,
        )

    @staticmethod
    def _source_type(item: dict, metadata: dict) -> str:
        raw = item.get("source_type") or metadata.get("source_type")
        normalized = str(raw or "").strip().lower()
        if normalized in {"document", "document_chunk", "chunk"}:
            return "document_chunk"
        if normalized in {"wiki", "wiki_page", "wiki-page"}:
            return "wiki_page"
        match_type = str(item.get("match_type") or metadata.get("match_type") or "").strip().lower()
        if match_type in {"wiki", "wiki_page", "4"}:
            return "wiki_page"
        if item.get("wiki_page_id") or item.get("wiki_id"):
            return "wiki_page"
        return "document_chunk"

    @staticmethod
    def _normalized_source_type(value: object) -> str | None:
        normalized = str(value or "").strip().lower()
        if normalized in {"document", "document_chunk", "chunk"}:
            return "document_chunk"
        if normalized in {"wiki", "wiki_page", "wiki-page"}:
            return "wiki_page"
        return None

    @staticmethod
    def _search_result_metadata(item: dict) -> dict:
        raw_metadata = item.get("metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        chunk_metadata = item.get("chunk_metadata")
        if isinstance(chunk_metadata, dict):
            metadata["chunk_metadata"] = chunk_metadata
        for key in (
            "knowledge_base_id",
            "knowledge_id",
            "chunk_index",
            "start_at",
            "end_at",
            "seq",
            "match_type",
            "sub_chunk_id",
            "chunk_type",
            "parent_chunk_id",
            "image_info",
            "knowledge_filename",
            "knowledge_source",
            "knowledge_channel",
            "matched_content",
            "knowledge_description",
            "wiki_page_id",
            "wiki_id",
            "wiki_page_slug",
            "page_id",
            "slug",
            "wiki_title",
            "page_title",
        ):
            if key in item and item.get(key) not in (None, ""):
                metadata[f"weknora_{key}"] = item.get(key)
        metadata["score_semantics"] = "weknora_rrf_or_backend_score"
        return metadata

    @staticmethod
    def _to_document_chunk_preview(item: dict, external_doc_id: str) -> dict:
        content = str(item.get("content") or "")
        raw_metadata = item.get("metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        for key in (
            "id",
            "seq_id",
            "knowledge_id",
            "knowledge_base_id",
            "tag_id",
            "chunk_index",
            "is_enabled",
            "status",
            "start_at",
            "end_at",
            "pre_chunk_id",
            "next_chunk_id",
            "chunk_type",
            "parent_chunk_id",
            "relation_chunks",
            "indirect_relation_chunks",
            "image_info",
            "created_at",
            "updated_at",
        ):
            if key in item and item.get(key) not in (None, ""):
                metadata[f"weknora_{key}"] = item.get(key)
        metadata["source"] = "weknora_api"
        return {
            "id": item.get("id"),
            "external_doc_id": item.get("knowledge_id") or external_doc_id,
            "chunk_index": int(item.get("chunk_index") or 0),
            "title": item.get("title"),
            "content": content,
            "content_hash": item.get("content_hash") or _content_hash(content),
            "token_count": int(item.get("token_count") or 0),
            "char_count": len(content),
            "start_char": _optional_int(item.get("start_at")),
            "end_char": _optional_int(item.get("end_at")),
            "page_number": _optional_int(item.get("page_number")),
            "section_path": item.get("section_path"),
            "paragraph_start_index": None,
            "paragraph_end_index": None,
            "source": "weknora_api",
            "metadata": metadata,
            "embedding_status": "indexed" if item.get("is_enabled", True) else "disabled",
            "vector_id": item.get("vector_id"),
        }

    @staticmethod
    def _to_wiki_page_summary(item: dict) -> WikiPageSummary:
        metadata = WeKnoraApiBackend._wiki_page_metadata(item)
        return WikiPageSummary(
            slug=str(item.get("slug") or item.get("id") or ""),
            title=str(item.get("title") or "Untitled"),
            page_type=str(item.get("page_type") or item.get("type") or "wiki"),
            summary=str(item.get("summary") or ""),
            source="weknora_api",
            metadata=metadata,
        )

    @staticmethod
    def _wiki_summary_dict(item: dict) -> dict:
        metadata = WeKnoraApiBackend._wiki_page_metadata(item)
        return {
            "id": _optional_str(metadata.get("id") or item.get("id")),
            "slug": _optional_str(item.get("slug") or item.get("id")) or "",
            "title": _optional_str(item.get("title")) or "Untitled",
            "page_type": _optional_str(item.get("page_type") or item.get("type") or "wiki"),
            "summary": _shorten(str(item.get("summary") or ""), 240),
            "status": _optional_str(metadata.get("status") or item.get("status")),
            "source_type": "wiki_page",
            "evidence_id": WeKnoraApiBackend._evidence_id(
                "wiki_page",
                None,
                _optional_str(metadata.get("id") or item.get("id") or item.get("slug")),
            ),
            "wiki_page_id": _optional_str(metadata.get("id") or item.get("id") or item.get("slug")),
        }

    @staticmethod
    def _wiki_index_entry_dict(item: dict) -> dict:
        wiki_page_id = _optional_str(item.get("id") or item.get("slug"))
        return {
            "slug": _optional_str(item.get("slug")) or "",
            "title": _optional_str(item.get("title")) or "Untitled",
            "summary": _shorten(str(item.get("summary") or ""), 240),
            "source_type": "wiki_page",
            "wiki_page_id": wiki_page_id,
            "evidence_id": WeKnoraApiBackend._evidence_id("wiki_page", None, wiki_page_id),
        }

    @staticmethod
    def _to_wiki_page(item: dict, fallback_slug: str) -> WikiPage:
        metadata = WeKnoraApiBackend._wiki_page_metadata(item)
        return WikiPage(
            slug=str(item.get("slug") or fallback_slug),
            title=str(item.get("title") or "Untitled"),
            page_type=str(item.get("page_type") or item.get("type") or "wiki"),
            summary=str(item.get("summary") or ""),
            content=str(item.get("content") or item.get("content_markdown") or ""),
            citations=[],
            source="weknora_api",
            metadata=metadata,
        )

    @staticmethod
    def _wiki_page_to_evidence(page: WikiPage, kb_id: str) -> Evidence:
        metadata = dict(page.metadata or {})
        wiki_page_id = str(
            metadata.get("id")
            or metadata.get("weknora_wiki_page_id")
            or metadata.get("wiki_page_id")
            or page.slug
        )
        metadata.setdefault("weknora_wiki_page_id", wiki_page_id)
        metadata.setdefault("weknora_wiki_page_slug", page.slug)
        metadata.setdefault("weknora_knowledge_base_id", kb_id)
        metadata.setdefault("citation_source_type", "wiki_page")
        evidence_id = f"wiki_page:{wiki_page_id}"
        metadata.setdefault("evidence_id", evidence_id)
        text = page.content or page.summary
        return Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            title=page.title or page.slug or "Untitled wiki page",
            text=text,
            score=None,
            source="weknora_api",
            metadata=metadata,
            evidence_id=evidence_id,
            source_type="wiki_page",
            wiki_page_id=wiki_page_id,
        )

    @staticmethod
    def _wiki_page_metadata(item: dict) -> dict:
        raw_page_metadata = item.get("page_metadata")
        metadata = dict(raw_page_metadata) if isinstance(raw_page_metadata, dict) else {}
        raw_metadata = item.get("metadata")
        if isinstance(raw_metadata, dict):
            metadata.update(raw_metadata)
        for key in (
            "id",
            "tenant_id",
            "knowledge_base_id",
            "status",
            "aliases",
            "source_refs",
            "chunk_refs",
            "in_links",
            "out_links",
            "version",
            "created_at",
            "updated_at",
        ):
            if key in item and item.get(key) not in (None, ""):
                metadata[key] = item.get(key)
        metadata["source"] = "weknora_api"
        return metadata

    @staticmethod
    def _evidence_id(
        source_type: str,
        chunk_id: str | None,
        wiki_page_id: str | None,
    ) -> str | None:
        if source_type == "document_chunk" and chunk_id:
            return f"document_chunk:{chunk_id}"
        if source_type == "wiki_page" and wiki_page_id:
            return f"wiki_page:{wiki_page_id}"
        return None


def _dedupe_evidence_items(items: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    deduped: list[Evidence] = []
    for item in items:
        key = (
            item.evidence_id
            or item.chunk_id
            or item.wiki_page_id
            or f"{item.source_type}:{item.title}:{item.text[:80]}"
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _interleave_evidence_sources(
    document_items: list[Evidence],
    wiki_items: list[Evidence],
) -> list[Evidence]:
    merged: list[Evidence] = []
    max_length = max(len(document_items), len(wiki_items))
    for index in range(max_length):
        if index < len(document_items):
            merged.append(document_items[index])
        if index < len(wiki_items):
            merged.append(wiki_items[index])
    return _dedupe_evidence_items(merged)


def _wiki_retrieval_queries(query: str, filters: dict | None = None) -> list[str]:
    """Build conservative Wiki-search variants without leaving Wiki-only mode."""

    raw_query = str(query or "").strip()
    variants: list[str] = [raw_query]
    filters = filters or {}
    variants.extend(_list_filter(filters.get("wiki_query_aliases")))

    normalized_query = _normalize_wiki_query_text(raw_query)
    if normalized_query and normalized_query != raw_query:
        variants.append(normalized_query)

    variants.extend(_wiki_phrase_variants(raw_query))

    code_terms = re.findall(r"[A-Za-z_]+=[A-Za-z_]+|TEST-[A-Z]+-\d{3}", raw_query)
    variants.extend(code_terms)

    keyword_query = _wiki_keyword_query(raw_query)
    if keyword_query and keyword_query not in {raw_query, normalized_query}:
        variants.append(keyword_query)

    return _dedupe_strings(variants)


def _wiki_phrase_variants(query: str) -> list[str]:
    variants: list[str] = []
    if all(term in query for term in ("关联", "政策", "法规", "案例")):
        variants.extend(
            [
                "关联政策 关联法规 关联案例",
                "时限管理 关联政策 关联法规 关联案例",
                "政策 法规 案例",
            ]
        )
    if "常见误区" in query or ("误区" in query and "Wiki" in query):
        variants.extend(["常见误区", "Wiki 常见误区", "时限管理 常见误区"])
    if "source_type=wiki_page" in query or ("evidence" in query and "区分" in query):
        variants.extend(
            [
                "source_type=wiki_page",
                "Wiki evidence source_type=wiki_page",
                "原始文档 evidence 区分",
                "发布后的 Wiki evidence 原始文档 evidence 区分",
            ]
        )
    return variants


def _normalize_wiki_query_text(query: str) -> str:
    normalized = re.sub(r"[？?，,。；;：:、（）()【】\[\]`\"']", " ", query)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _wiki_keyword_query(query: str) -> str:
    normalized = _normalize_wiki_query_text(query)
    if not normalized:
        return ""
    stop_terms = (
        "哪些",
        "什么",
        "应该",
        "如何",
        "指出",
        "发布后的",
        "发布后",
        "专题中",
        "专题",
        "原始",
        "文档",
    )
    compact = normalized
    for term in stop_terms:
        compact = compact.replace(term, " ")
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _string_metadata(metadata: dict) -> dict[str, str]:
    output: dict[str, str] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, tuple)):
            output[str(key)] = json.dumps(value, ensure_ascii=False, default=str)
        else:
            output[str(key)] = str(value)
    return output


def _bool_string(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "true" if str(value).strip().lower() in {"1", "true", "yes", "on"} else "false"


def _list_filter(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        values = [str(part).strip() for part in value]
    else:
        values = [str(value).strip()]
    return [item for item in values if item]


def _knowledge_scope_filter(filters: dict) -> list[str]:
    return _list_filter(
        filters.get("knowledge_ids")
        or filters.get("document_ids")
        or filters.get("external_doc_ids")
        or filters.get("external_doc_id")
    )


def _items_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "list", "records", "knowledge_bases", "tags"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    nested = payload.get("data")
    if nested is not payload:
        nested_items = _items_from_payload(nested)
        if nested_items:
            return nested_items
    return [payload]


def _knowledge_tag_safe_dict(item: dict) -> dict:
    return {
        "id": _optional_str(item.get("id")),
        "seq_id": _optional_int(item.get("seq_id")),
        "knowledge_base_id": _optional_str(item.get("knowledge_base_id")),
        "name": _optional_str(item.get("name")),
        "color": _optional_str(item.get("color")),
        "sort_order": _optional_int(item.get("sort_order")),
        "knowledge_count": _optional_int(item.get("knowledge_count")),
        "chunk_count": _optional_int(item.get("chunk_count")),
        "source": "weknora_api",
    }


def _multipart_body(boundary: str, file_path: Path, fields: dict[str, str]) -> bytes:
    if not file_path.is_file():
        raise KnowledgeBackendUnavailableError(f"Document file does not exist: {file_path}")
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.extend(
            [
                f"--{boundary}".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"),
                b"",
                value.encode("utf-8"),
            ]
        )
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    lines.extend(
        [
            f"--{boundary}".encode("utf-8"),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"'
            ).encode("utf-8"),
            f"Content-Type: {content_type}".encode("utf-8"),
            b"",
            file_path.read_bytes(),
            f"--{boundary}--".encode("utf-8"),
            b"",
        ]
    )
    return b"\r\n".join(lines)


def _shorten(value: str, limit: int = 240) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_mapping(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, item in value.items():
        parsed = _optional_int(item)
        if parsed is not None:
            result[str(key)] = parsed
    return result


def _elapsed_ms(started: float) -> int:
    return max(round((time.perf_counter() - started) * 1000), 0)


def _log_excerpt(value: str | None, limit: int = WEKNORA_LOG_EXCERPT_LIMIT) -> str | None:
    if not value:
        return None
    return _shorten(_redact_sensitive_text(value), limit)


def _log_weknora_call(
    *,
    request_id: str,
    operation: str,
    status: str,
    status_code: int | None,
    duration_ms: int,
    retry_count: int,
    error_code: str | None = None,
    excerpt: str | None = None,
) -> None:
    payload = {
        "event": "weknora_adapter_call",
        "source": "weknora_api",
        "request_id": _redact_sensitive_text(request_id),
        "adapter_operation_id": _redact_sensitive_text(request_id),
        "operation": _sanitize_operation(operation),
        "status": status,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "retry_count": retry_count,
        "error_code": _redact_sensitive_text(error_code or "") or None,
        "excerpt": _log_excerpt(excerpt),
        **{
            key: _redact_sensitive_text(value)
            for key, value in current_weknora_log_context().items()
        },
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    message = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if status == "error":
        WEKNORA_LOGGER.warning(message)
    else:
        WEKNORA_LOGGER.info(message)


def _sanitize_operation(operation: str) -> str:
    method, _, path = operation.partition(" ")
    if not path:
        path = method
        method = ""
    path = path.split("?", 1)[0]
    safe = f"{method} {path}".strip()
    return _shorten(_redact_sensitive_text(safe), 120)


def _http_error_to_weknora_error(
    status_code: int,
    body_text: str,
    operation: str,
) -> WeKnoraUnavailableError:
    detail = _extract_error_detail(body_text)
    message = _public_http_error_message(status_code, detail)
    if status_code in {401, 403}:
        return WeKnoraAuthError(
            message,
            error_code=f"weknora_http_{status_code}",
            status_code=status_code,
            operation=operation,
            retryable=False,
        )
    if status_code == 404:
        return WeKnoraNotFoundError(
            message,
            error_code="weknora_http_404",
            status_code=status_code,
            operation=operation,
            retryable=False,
        )
    if status_code == 429:
        return WeKnoraRateLimitError(
            message,
            error_code="weknora_http_429",
            status_code=status_code,
            operation=operation,
            retryable=True,
        )
    if 500 <= status_code <= 599:
        return WeKnoraServerError(
            message,
            error_code=f"weknora_http_{status_code}",
            status_code=status_code,
            operation=operation,
            retryable=True,
        )
    return WeKnoraUnavailableError(
        message,
        error_code=f"weknora_http_{status_code}",
        status_code=status_code,
        operation=operation,
        retryable=False,
    )


def _extract_error_detail(body_text: str) -> str:
    if not body_text:
        return ""
    try:
        parsed = json.loads(body_text)
    except json.JSONDecodeError:
        return _shorten(_redact_sensitive_text(body_text), 160)
    values: list[object] = []
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            values.extend(
                [
                    error.get("code"),
                    error.get("error_code"),
                    error.get("message"),
                ]
            )
        elif error:
            values.append(error)
        values.extend(
            [
                parsed.get("error_code"),
                parsed.get("code"),
                parsed.get("message"),
                parsed.get("detail"),
            ]
        )
    elif isinstance(parsed, list):
        values.append(f"{len(parsed)} error items")
    detail = " ".join(str(value) for value in values if value not in (None, ""))
    return _shorten(_redact_sensitive_text(detail), 160)


def _public_http_error_message(status_code: int, detail: str) -> str:
    fallback_by_status = {
        401: "WeKnora authentication failed",
        403: "WeKnora authorization failed",
        404: "WeKnora resource was not found",
        429: "WeKnora rate limit reached",
    }
    if 500 <= status_code <= 599:
        fallback = "WeKnora server returned a retryable error"
    else:
        fallback = fallback_by_status.get(status_code, "WeKnora request failed")
    if not detail:
        return fallback
    return f"{fallback}: {detail}"


def _url_error_is_timeout(exc: URLError) -> bool:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(reason).lower()


def _redact_sensitive_text(value: str) -> str:
    redacted = re.sub(
        r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [redacted]",
        value,
    )
    redacted = re.sub(
        r"(?i)(authorization|x-api-key|api[_-]?key|token|secret|password)(\s*[:=]\s*)\S+",
        r"\1\2[redacted]",
        redacted,
    )
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "sk-[redacted]", redacted)
    redacted = re.sub(r"https?://[^\s\"'<>]+", "https://[redacted]", redacted)
    return redacted


def _content_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
