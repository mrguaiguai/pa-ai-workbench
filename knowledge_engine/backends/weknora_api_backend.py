import json
import os
from pathlib import Path
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


class WeKnoraApiBackend(KnowledgeEngine):
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("WEKNORA_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("WEKNORA_API_KEY", "")
        self.timeout = timeout

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
        payload = {
            "file_path": file_path,
            "metadata": metadata,
        }
        data = self._request_json("POST", "/api/documents", payload)
        if not isinstance(data, dict):
            raise KnowledgeBackendUnavailableError("WeKnora upload returned invalid JSON")
        external_doc_id = data.get("external_doc_id") or data.get("id")
        return KnowledgeDocument(
            document_id=metadata.get("document_id"),
            external_doc_id=external_doc_id,
            title=data.get("title") or metadata.get("title") or Path(file_path).name,
            status=data.get("status", "uploaded"),
            source="weknora_api",
            metadata=data.get("metadata") or metadata,
        )

    def get_document_status(self, external_doc_id: str) -> dict:
        self._require_configured()
        data = self._request_json("GET", f"/api/documents/{external_doc_id}/status")
        if not isinstance(data, dict):
            data = {}
        return {
            "external_doc_id": external_doc_id,
            "status": data.get("status", "unknown"),
            "source": "weknora_api",
            "metadata": data.get("metadata", {}),
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
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise KnowledgeBackendUnavailableError("WeKnora API request failed") from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise KnowledgeBackendUnavailableError("WeKnora API returned invalid JSON") from exc

    def _require_configured(self) -> None:
        if not self.configured:
            raise KnowledgeBackendUnavailableError("WEKNORA_BASE_URL is not configured")

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
