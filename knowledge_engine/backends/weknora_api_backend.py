import json
import mimetypes
import os
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
        payload = self._retrieve_payload(normalized_query, filters)
        data = self._request_json("POST", "/api/v1/knowledge-search", payload)
        items = self._unwrap_items(data)
        source_type_filter = self._normalized_source_type(filters.get("source_type"))
        evidence_items = [self._to_evidence(item) for item in items if isinstance(item, dict)]
        if source_type_filter:
            evidence_items = [
                evidence
                for evidence in evidence_items
                if evidence.source_type == source_type_filter
            ]
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

    def _retrieve_payload(self, query: str, filters: dict) -> dict:
        payload: dict[str, object] = {"query": query}
        knowledge_base_ids = _list_filter(
            filters.get("knowledge_base_ids")
            or filters.get("knowledge_base_id")
            or filters.get("kb_ids")
            or filters.get("kb_id")
        )
        if not knowledge_base_ids and self.default_kb_id:
            knowledge_base_ids = [self.default_kb_id]
        if knowledge_base_ids:
            payload["knowledge_base_ids"] = knowledge_base_ids

        knowledge_ids = _list_filter(
            filters.get("knowledge_ids")
            or filters.get("document_ids")
            or filters.get("external_doc_ids")
            or filters.get("external_doc_id")
        )
        if knowledge_ids:
            payload["knowledge_ids"] = knowledge_ids
        return payload

    def _wiki_kb_id(self, kb_id: str | None = None) -> str:
        resolved = (kb_id or self.default_kb_id or "").strip()
        if not resolved:
            raise KnowledgeBackendUnavailableError("WEKNORA_DEFAULT_KB_ID is not configured")
        return resolved

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
    def _to_evidence(item: dict) -> Evidence:
        metadata = WeKnoraApiBackend._search_result_metadata(item)
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


def _content_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
