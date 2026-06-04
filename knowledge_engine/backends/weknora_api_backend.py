import json
import mimetypes
import os
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary


def _get_timeout_seconds(default: float) -> float:
    value = os.getenv("WEKNORA_TIMEOUT_SECONDS")
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class WeKnoraApiBackend(KnowledgeEngine):
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        workspace_id: str | None = None,
        default_kb_id: str | None = None,
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

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def health(self) -> dict:
        if not self.configured:
            return {
                "status": "unavailable",
                "backend": "weknora_api",
                "configured": False,
                "source": "weknora_api",
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
            }
        if not isinstance(data, dict):
            data = {}
        return {
            "status": data.get("status", "ok"),
            "backend": "weknora_api",
            "configured": True,
            "source": "weknora_api",
        }

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        self._require_configured()
        if not self.default_kb_id:
            raise KnowledgeBackendUnavailableError("WEKNORA_DEFAULT_KB_ID is not configured")
        path = Path(file_path)
        fields = {
            "metadata": json.dumps(_string_metadata(metadata), ensure_ascii=False),
            "fileName": str(metadata.get("file_name") or path.name),
            "channel": str(metadata.get("weknora_channel") or "api"),
        }
        if metadata.get("tag_id"):
            fields["tag_id"] = str(metadata["tag_id"])
        if metadata.get("enable_multimodel") is not None:
            fields["enable_multimodel"] = _bool_string(metadata["enable_multimodel"])
        data = self._request_multipart_json(
            "/api/v1/knowledge-bases/{kb_id}/knowledge/file".format(
                kb_id=self.default_kb_id
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
            metadata=self._document_metadata(data, metadata),
        )

    def get_document_status(self, external_doc_id: str) -> dict:
        self._require_configured()
        data = self._request_json("GET", f"/api/v1/knowledge/{external_doc_id}")
        data = self._unwrap_data(data)
        if not isinstance(data, dict):
            data = {}
        raw_status = data.get("parse_status") or data.get("status")
        return {
            "external_doc_id": external_doc_id,
            "status": self._map_document_status(raw_status),
            "source": "weknora_api",
            "message": self._status_message(data),
            "failed_step": "weknora" if self._map_document_status(raw_status) == "failed" else None,
            "error_message": data.get("error_message") or None,
            "metadata": self._document_metadata(data, {}),
        }

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        self._require_configured()
        payload = {
            "query": query,
            "filters": filters or {},
            "top_k": top_k,
        }
        data = self._request_json("POST", "/api/retrieve", payload)
        items = data.get("items", []) if isinstance(data, dict) else data
        return [self._to_evidence(item) for item in items]

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        self._require_configured()
        query_params = {"query": query, "limit": limit}
        if kb_id:
            query_params["kb_id"] = kb_id
        data = self._request_json("GET", f"/api/wiki/search?{urlencode(query_params)}")
        items = data.get("items", []) if isinstance(data, dict) else data
        return [
            WikiPageSummary(
                slug=item.get("slug", item.get("id", "")),
                title=item.get("title", "Untitled"),
                page_type=item.get("page_type", item.get("type", "wiki")),
                summary=item.get("summary", ""),
                source="weknora_api",
                metadata=item.get("metadata", {}),
            )
            for item in items
        ]

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        self._require_configured()
        query_params = {"kb_id": kb_id} if kb_id else {}
        suffix = f"?{urlencode(query_params)}" if query_params else ""
        data = self._request_json("GET", f"/api/wiki/pages/{slug}{suffix}")
        if not data or not isinstance(data, dict):
            return None
        citations = [self._to_evidence(item) for item in data.get("citations", [])]
        return WikiPage(
            slug=data.get("slug", slug),
            title=data.get("title", "Untitled"),
            page_type=data.get("page_type", data.get("type", "wiki")),
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            citations=citations,
            source="weknora_api",
            metadata=data.get("metadata", {}),
        )

    def _request_json(self, method: str, path: str, payload: dict | None = None) -> dict | list:
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
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise KnowledgeBackendUnavailableError(
                f"WeKnora API request failed with HTTP {exc.code}: {_shorten(body_text)}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise KnowledgeBackendUnavailableError("WeKnora API request failed") from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise KnowledgeBackendUnavailableError("WeKnora API returned invalid JSON") from exc

    def _request_multipart_json(
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
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise KnowledgeBackendUnavailableError(
                f"WeKnora upload failed with HTTP {exc.code}: {_shorten(body_text)}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise KnowledgeBackendUnavailableError("WeKnora upload request failed") from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise KnowledgeBackendUnavailableError("WeKnora upload returned invalid JSON") from exc

    def _require_configured(self) -> None:
        if not self.configured:
            raise KnowledgeBackendUnavailableError("WEKNORA_BASE_URL is not configured")

    def _apply_auth_headers(self, headers: dict[str, str]) -> None:
        if not self.service_token:
            return
        headers["X-API-Key"] = self.service_token
        headers["Authorization"] = f"Bearer {self.service_token}"

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
        if normalized in {"failed", "error", "cancelled"}:
            return "failed"
        return "unknown"

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
    def _to_evidence(item: dict) -> Evidence:
        metadata = dict(item.get("metadata", {}) or {})
        source_type = WeKnoraApiBackend._source_type(item, metadata)
        chunk_id = item.get("chunk_id")
        wiki_page_id = item.get("wiki_page_id") or item.get("wiki_id")
        evidence_id = (
            item.get("evidence_id")
            or metadata.get("evidence_id")
            or WeKnoraApiBackend._evidence_id(source_type, chunk_id, wiki_page_id)
        )
        metadata.setdefault("evidence_id", evidence_id)
        metadata.setdefault("citation_source_type", source_type)
        return Evidence(
            document_id=item.get("document_id"),
            external_doc_id=item.get("external_doc_id") or item.get("doc_id"),
            chunk_id=chunk_id,
            title=item.get("title", "Untitled evidence"),
            text=item.get("text", item.get("content", "")),
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
        if item.get("wiki_page_id") or item.get("wiki_id"):
            return "wiki_page"
        return "document_chunk"

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
