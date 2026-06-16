"""Current-run corpus isolation helpers for Phase 5 acceptance.

The helpers are intentionally PA-side and backend-neutral. They let acceptance
runs pass a small current_run scope with the identifiers observed during upload,
then enforce that scope again after retrieval in case the backend ignores or
only partially supports the requested filter.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Any

from knowledge_engine.retrieval import RETRIEVAL_OPTIONS_KEY
from knowledge_engine.schemas import Evidence


CURRENT_RUN_FILTER_KEY = "current_run"
CURRENT_RUN_WARNING_METADATA_KEY = "current_run_isolation_warnings"


@dataclass(frozen=True)
class CurrentRunScope:
    run_id: str | None = None
    corpus_id: str | None = None
    namespace: str | None = None
    document_ids: tuple[str, ...] = field(default_factory=tuple)
    external_doc_ids: tuple[str, ...] = field(default_factory=tuple)
    knowledge_ids: tuple[str, ...] = field(default_factory=tuple)
    wiki_page_ids: tuple[str, ...] = field(default_factory=tuple)
    anchors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_filter_terms(self) -> bool:
        return any(
            (
                self.run_id,
                self.corpus_id,
                self.namespace,
                self.document_ids,
                self.external_doc_ids,
                self.knowledge_ids,
                self.wiki_page_ids,
                self.anchors,
            )
        )

    @property
    def has_backend_knowledge_scope(self) -> bool:
        return bool(self.knowledge_ids or self.external_doc_ids)

    def to_filter_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.run_id:
            payload["run_id"] = self.run_id
        if self.corpus_id:
            payload["corpus_id"] = self.corpus_id
        if self.namespace:
            payload["namespace"] = self.namespace
        if self.document_ids:
            payload["document_ids"] = list(self.document_ids)
        if self.external_doc_ids:
            payload["external_doc_ids"] = list(self.external_doc_ids)
        if self.knowledge_ids:
            payload["knowledge_ids"] = list(self.knowledge_ids)
        if self.wiki_page_ids:
            payload["wiki_page_ids"] = list(self.wiki_page_ids)
        if self.anchors:
            payload["anchors"] = list(self.anchors)
        return payload


@dataclass(frozen=True)
class PreparedCurrentRunFilters:
    filters: dict[str, Any]
    scope: CurrentRunScope | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CurrentRunIsolationResult:
    items: list[Evidence]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    dropped_count: int = 0


def prepare_current_run_filters(filters: dict[str, Any] | None) -> PreparedCurrentRunFilters:
    """Normalize a current_run filter and add backend knowledge scope when possible."""

    effective = {
        str(key): value
        for key, value in (filters or {}).items()
        if value is not None
    }
    scope = _scope_from_filters(effective)
    if scope is None:
        return PreparedCurrentRunFilters(filters=effective)

    warnings: list[str] = []
    effective[CURRENT_RUN_FILTER_KEY] = scope.to_filter_dict()

    backend_scope = _unique((*scope.knowledge_ids, *scope.external_doc_ids))
    if backend_scope:
        existing_knowledge_ids = _list_filter(effective.get("knowledge_ids"))
        effective["knowledge_ids"] = _unique((*existing_knowledge_ids, *backend_scope))
    elif scope.document_ids:
        warnings.append(
            "Current-run isolation has only PA document_ids; backend retrieval may need PA-side post-filtering."
        )
    elif scope.has_filter_terms:
        warnings.append(
            "Current-run isolation has no backend knowledge ids; PA-side post-filtering is required."
        )

    return PreparedCurrentRunFilters(
        filters=effective,
        scope=scope,
        warnings=tuple(warnings),
    )


def apply_current_run_isolation(
    evidence_items: list[Evidence],
    scope: CurrentRunScope | None,
) -> CurrentRunIsolationResult:
    """Drop evidence that cannot be tied to the current acceptance run."""

    if scope is None or not scope.has_filter_terms:
        return CurrentRunIsolationResult(items=evidence_items)

    kept: list[Evidence] = []
    dropped = 0
    for evidence in evidence_items:
        if _matches_scope(evidence, scope):
            kept.append(_attach_scope_metadata(evidence, scope))
        else:
            dropped += 1

    warnings: list[str] = []
    if dropped:
        warnings.append(
            f"Current-run isolation dropped {dropped} evidence item(s) outside the requested scope."
        )
    if evidence_items and not kept:
        warnings.append(
            "Current-run isolation removed all retrieved evidence; do not mark this acceptance run PASS."
        )

    return CurrentRunIsolationResult(
        items=kept,
        warnings=tuple(warnings),
        dropped_count=dropped,
    )


def attach_current_run_warnings(
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
                CURRENT_RUN_WARNING_METADATA_KEY: list(warnings),
            },
        )
        for evidence in evidence_items
    ]


def current_run_fetch_top_k(top_k: int, scope: CurrentRunScope | None) -> int:
    normalized = max(top_k, 0)
    if normalized == 0:
        return 0
    if scope is None or not scope.has_filter_terms:
        return max(normalized * 2, normalized)
    return max(normalized * 4, normalized + 8, normalized)


def _scope_from_filters(filters: dict[str, Any]) -> CurrentRunScope | None:
    raw = filters.get(CURRENT_RUN_FILTER_KEY)
    if raw in (None, "", False):
        return None
    if isinstance(raw, str):
        raw_scope: dict[str, Any] = {"run_id": raw}
    elif isinstance(raw, dict):
        raw_scope = raw
    else:
        raw_scope = {}

    scope = CurrentRunScope(
        run_id=_optional_str(raw_scope.get("run_id") or raw_scope.get("id")),
        corpus_id=_optional_str(raw_scope.get("corpus_id")),
        namespace=_optional_str(raw_scope.get("namespace")),
        document_ids=tuple(
            _unique(
                _list_filter(raw_scope.get("document_ids"))
                + _list_filter(raw_scope.get("pa_document_ids"))
            )
        ),
        external_doc_ids=tuple(
            _unique(
                _list_filter(raw_scope.get("external_doc_ids"))
                + _list_filter(raw_scope.get("external_doc_id"))
            )
        ),
        knowledge_ids=tuple(
            _unique(
                _list_filter(raw_scope.get("knowledge_ids"))
                + _list_filter(raw_scope.get("weknora_knowledge_ids"))
            )
        ),
        wiki_page_ids=tuple(
            _unique(
                _list_filter(raw_scope.get("wiki_page_ids"))
                + _list_filter(raw_scope.get("wiki_page_id"))
                + _list_filter(raw_scope.get("weknora_wiki_page_ids"))
            )
        ),
        anchors=tuple(_unique(_list_filter(raw_scope.get("anchors")))),
    )
    return scope if scope.has_filter_terms else None


def _matches_scope(evidence: Evidence, scope: CurrentRunScope) -> bool:
    identifiers = _evidence_identifiers(evidence)
    has_document_scope = bool(
        scope.document_ids or scope.external_doc_ids or scope.knowledge_ids
    )
    if scope.document_ids and identifiers["document_ids"] & set(scope.document_ids):
        return True
    if scope.external_doc_ids and identifiers["external_doc_ids"] & set(scope.external_doc_ids):
        return True
    if scope.knowledge_ids and identifiers["external_doc_ids"] & set(scope.knowledge_ids):
        return True
    if scope.wiki_page_ids and identifiers["wiki_page_ids"] & set(scope.wiki_page_ids):
        return True
    if evidence.source_type == "wiki_page" and scope.wiki_page_ids:
        return False
    metadata_terms = identifiers["metadata_terms"]
    if scope.run_id and scope.run_id in metadata_terms:
        return True
    if scope.corpus_id and scope.corpus_id in metadata_terms:
        return True
    if scope.namespace and scope.namespace in metadata_terms:
        return True
    if has_document_scope:
        if (
            evidence.source_type == "wiki_page"
            and scope.anchors
            and identifiers["anchors"] & set(scope.anchors)
        ):
            return True
        return False
    if scope.anchors and identifiers["anchors"] & set(scope.anchors):
        return True
    return False


def _attach_scope_metadata(evidence: Evidence, scope: CurrentRunScope) -> Evidence:
    scope_metadata = {
        "current_run_isolated": True,
        "current_run_scope": scope.to_filter_dict(),
    }
    if scope.run_id:
        scope_metadata["current_run_id"] = scope.run_id
    if scope.corpus_id:
        scope_metadata["current_run_corpus_id"] = scope.corpus_id
    if scope.namespace:
        scope_metadata["current_run_namespace"] = scope.namespace
    return replace(evidence, metadata={**evidence.metadata, **scope_metadata})


def _evidence_identifiers(evidence: Evidence) -> dict[str, set[str]]:
    metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
    document_ids = {
        *_value_set(evidence.document_id),
        *_metadata_value_set(metadata, "document_id", "pa_document_id"),
    }
    external_doc_ids = {
        *_value_set(evidence.external_doc_id),
        *_metadata_value_set(
            metadata,
            "external_doc_id",
            "knowledge_id",
            "weknora_id",
            "weknora_knowledge_id",
            "weknora_external_doc_id",
        ),
    }
    wiki_page_ids = {
        *_value_set(evidence.wiki_page_id),
        *_metadata_value_set(
            metadata,
            "wiki_page_id",
            "wiki_page_ids",
            "weknora_wiki_page_id",
            "weknora_wiki_page_ids",
            "pa_wiki_page_id",
            "id",
            "slug",
            "weknora_wiki_page_slug",
        ),
    }
    anchors = _metadata_value_set(metadata, "anchor", "anchors", "test_anchor", "expected_anchor")
    metadata_terms = _metadata_value_set(
        metadata,
        "current_run_id",
        "phase5_run_id",
        "corpus_id",
        "current_run_corpus_id",
        "namespace",
        "current_run_namespace",
    )
    return {
        "document_ids": document_ids,
        "external_doc_ids": external_doc_ids,
        "wiki_page_ids": wiki_page_ids,
        "anchors": anchors,
        "metadata_terms": metadata_terms,
    }


def _metadata_value_set(metadata: dict[str, Any], *keys: str) -> set[str]:
    values: list[str] = []
    for key in keys:
        values.extend(_list_filter(metadata.get(key)))
    return set(values)


def _list_filter(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    return [item for item in (_optional_str(item) for item in values) if item]


def _value_set(value: Any) -> set[str]:
    return set(_list_filter(value))


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _optional_str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
