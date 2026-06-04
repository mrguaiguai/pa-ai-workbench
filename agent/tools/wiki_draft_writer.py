from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
import re
from typing import Any


@dataclass(frozen=True)
class WikiDraftRequest:
    output_id: str
    slug: str | None = None
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    business_area: str | None = None
    page_type: str | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WikiDraftResult:
    slug: str
    title: str
    status: str = "draft"
    source_output_id: str | None = None
    page_type: str | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class WikiDraftWriterError(ValueError):
    pass


class InMemoryWikiDraftWriter:
    def __init__(self) -> None:
        self._drafts: dict[str, WikiDraftResult] = {}

    def __call__(self, request: WikiDraftRequest) -> WikiDraftResult:
        slug = request.slug or self._slug_from_request(request)
        result = WikiDraftResult(
            slug=self._unique_slug(slug),
            title=request.title or f"Wiki draft from {request.output_id}",
            status="draft",
            source_output_id=request.output_id,
            page_type=request.page_type,
            summary=request.summary,
            tags=list(request.tags or []),
            metadata={
                **request.metadata,
                "mock": True,
                "source": "in_memory_wiki_draft_writer",
            },
        )
        self._drafts[result.slug] = result
        return result

    def get(self, slug: str) -> WikiDraftResult | None:
        return self._drafts.get(slug)

    @staticmethod
    def _slug_from_request(request: WikiDraftRequest) -> str:
        base = request.title or request.output_id
        normalized = re.sub(r"[^a-z0-9]+", "-", base.strip().lower()).strip("-")
        return normalized or f"wiki-draft-{request.output_id}"

    def _unique_slug(self, slug: str) -> str:
        candidate = slug
        index = 2
        while candidate in self._drafts:
            candidate = f"{slug}-{index}"
            index += 1
        return candidate


class WikiDraftWriterTool:
    def __init__(
        self,
        draft_writer: Callable[[WikiDraftRequest], Any] | None = None,
    ) -> None:
        self.draft_writer = draft_writer or InMemoryWikiDraftWriter()

    def write_from_output(
        self,
        output_id: str,
        slug: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        business_area: str | None = None,
        page_type: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WikiDraftResult:
        normalized_output_id = output_id.strip()
        if not normalized_output_id:
            raise WikiDraftWriterError("output_id is required to create a Wiki draft.")
        request = WikiDraftRequest(
            output_id=normalized_output_id,
            slug=slug.strip() if slug else None,
            title=title.strip() if title else None,
            summary=summary,
            tags=tags,
            business_area=business_area,
            page_type=page_type,
            created_by=created_by,
            metadata=metadata or {},
        )
        return self._normalize_result(self.draft_writer(request), request)

    @classmethod
    def _normalize_result(cls, value: Any, request: WikiDraftRequest) -> WikiDraftResult:
        if isinstance(value, WikiDraftResult):
            return value
        if isinstance(value, dict):
            return cls._result_from_mapping(value, request)
        return cls._result_from_object(value, request)

    @classmethod
    def _result_from_mapping(
        cls,
        value: dict[str, Any],
        request: WikiDraftRequest,
    ) -> WikiDraftResult:
        return WikiDraftResult(
            slug=str(value.get("slug") or request.slug or ""),
            title=str(value.get("title") or request.title or ""),
            status=str(value.get("status") or "draft"),
            source_output_id=cls._optional_str(
                value.get("source_output_id") or request.output_id
            ),
            page_type=cls._optional_str(value.get("page_type") or request.page_type),
            summary=cls._optional_str(value.get("summary") or request.summary),
            tags=cls._list_value(value.get("tags") or request.tags),
            metadata=cls._dict_value(value.get("metadata")),
        )

    @classmethod
    def _result_from_object(cls, value: Any, request: WikiDraftRequest) -> WikiDraftResult:
        return WikiDraftResult(
            slug=str(getattr(value, "slug", None) or request.slug or ""),
            title=str(getattr(value, "title", None) or request.title or ""),
            status=str(getattr(value, "status", None) or "draft"),
            source_output_id=cls._optional_str(
                getattr(value, "source_output_id", None) or request.output_id
            ),
            page_type=cls._optional_str(
                getattr(value, "page_type", None) or request.page_type
            ),
            summary=cls._optional_str(getattr(value, "summary", None) or request.summary),
            tags=cls._list_value(getattr(value, "tags", None) or request.tags),
            metadata=cls._dict_value(getattr(value, "metadata", None)),
        )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _list_value(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _dict_value(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}
