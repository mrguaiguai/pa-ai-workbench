from app import pathing as _pathing  # noqa: F401

from dataclasses import dataclass
from typing import Any

from knowledge_engine.current_run import apply_current_run_isolation
from knowledge_engine.current_run import attach_current_run_warnings
from knowledge_engine.current_run import current_run_fetch_top_k
from knowledge_engine.current_run import prepare_current_run_filters
from knowledge_engine.evidence import normalize_evidence_results
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import Evidence


@dataclass(frozen=True)
class RetrievalContext:
    items: list[Evidence]
    filters: dict[str, Any]
    warnings: list[str]


def retrieve_evidence(
    query: str,
    filters: dict | None = None,
    top_k: int = 8,
) -> list[Evidence]:
    return retrieve_evidence_with_context(
        query=query,
        filters=filters,
        top_k=top_k,
    ).items


def retrieve_evidence_with_context(
    query: str,
    filters: dict | None = None,
    top_k: int = 8,
) -> RetrievalContext:
    engine = create_knowledge_engine()
    normalized_top_k = max(top_k, 0)
    prepared = prepare_current_run_filters(filters or {})
    raw_items = engine.retrieve(
        query=query,
        filters=prepared.filters,
        top_k=current_run_fetch_top_k(normalized_top_k, prepared.scope),
    )
    isolated = apply_current_run_isolation(raw_items, prepared.scope)
    warnings = [*prepared.warnings, *isolated.warnings]
    normalized = normalize_evidence_results(
        attach_current_run_warnings(isolated.items, warnings),
        top_k=normalized_top_k,
    )
    return RetrievalContext(
        items=normalized,
        filters=prepared.filters,
        warnings=warnings,
    )
