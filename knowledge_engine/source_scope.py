"""Source-scope normalization and PA-side enforcement for retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Any

from knowledge_engine.schemas import Evidence


SOURCE_SCOPE_FILTER_KEY = "source_scope"
SOURCE_SCOPE_WARNING_METADATA_KEY = "source_scope_warnings"
ALLOWED_SOURCE_SCOPES = {"all", "document", "wiki"}


@dataclass(frozen=True)
class PreparedSourceScopeFilters:
    filters: dict[str, Any]
    scope: str = "all"


@dataclass(frozen=True)
class SourceScopeResult:
    items: list[Evidence]
    warnings: tuple[str, ...] = ()
    dropped_count: int = 0


def prepare_source_scope_filters(filters: dict[str, Any] | None) -> PreparedSourceScopeFilters:
    effective = {
        str(key): value
        for key, value in (filters or {}).items()
        if value is not None
    }
    scope = normalize_source_scope(
        effective.get(SOURCE_SCOPE_FILTER_KEY)
        or effective.get("source_type")
        or effective.get("source")
        or effective.get("sourceType")
    )
    effective.pop(SOURCE_SCOPE_FILTER_KEY, None)
    for alias in ("source", "sourceType"):
        effective.pop(alias, None)
    if scope == "document":
        effective["source_type"] = "document_chunk"
    elif scope == "wiki":
        effective["source_type"] = "wiki_page"
    elif effective.get("source_type") in {"all", ""}:
        effective.pop("source_type", None)
    return PreparedSourceScopeFilters(filters=effective, scope=scope)


def apply_source_scope(
    evidence_items: list[Evidence],
    scope: str,
) -> SourceScopeResult:
    normalized_scope = normalize_source_scope(scope)
    if normalized_scope == "all":
        return SourceScopeResult(
            items=[_attach_scope_metadata(item, normalized_scope) for item in evidence_items],
        )

    expected_type = "document_chunk" if normalized_scope == "document" else "wiki_page"
    kept: list[Evidence] = []
    dropped = 0
    for item in evidence_items:
        if normalize_source_type(item.source_type or item.metadata.get("source_type")) == expected_type:
            kept.append(_attach_scope_metadata(item, normalized_scope))
        else:
            dropped += 1

    warnings: list[str] = []
    if dropped:
        warnings.append(
            f"Source scope '{normalized_scope}' dropped {dropped} evidence item(s) with mismatched source_type."
        )
    if evidence_items and not kept:
        warnings.append(
            f"Source scope '{normalized_scope}' removed all retrieved evidence; treat this as an empty scoped result."
        )
    return SourceScopeResult(
        items=kept,
        warnings=tuple(warnings),
        dropped_count=dropped,
    )


def attach_source_scope_warnings(
    evidence_items: list[Evidence],
    warnings: list[str] | tuple[str, ...],
) -> list[Evidence]:
    if not warnings:
        return evidence_items
    return [
        replace(
            evidence,
            metadata={
                **evidence.metadata,
                SOURCE_SCOPE_WARNING_METADATA_KEY: list(warnings),
            },
        )
        for evidence in evidence_items
    ]


def source_scope_fetch_top_k(top_k: int, scope: str) -> int:
    normalized = max(top_k, 0)
    if normalized == 0:
        return 0
    if normalize_source_scope(scope) == "all":
        return max(normalized * 2, normalized)
    return max(normalized * 4, normalized + 8, normalized)


def normalize_source_scope(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized or normalized == "all":
        return "all"
    if normalized in {"document", "documents", "doc", "chunk", "document_chunk"}:
        return "document"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki"
    raise ValueError("source_scope must be all, document, or wiki")


def normalize_source_type(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "documents", "doc", "chunk", "document_chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or "unknown"


def _attach_scope_metadata(evidence: Evidence, scope: str) -> Evidence:
    return replace(
        evidence,
        metadata={
            **evidence.metadata,
            "source_scope": scope,
        },
    )
