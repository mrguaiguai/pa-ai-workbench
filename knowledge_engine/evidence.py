from dataclasses import replace
from typing import Any

from knowledge_engine.schemas import Evidence


def normalize_evidence_results(
    evidence_items: list[Evidence],
    top_k: int | None = None,
) -> list[Evidence]:
    """Deduplicate retrieved evidence and attach display-only rank/score metadata."""

    limit = max(top_k, 0) if top_k is not None else None
    normalized: list[Evidence] = []
    seen: set[tuple[str, str]] = set()

    for raw_rank, evidence in enumerate(evidence_items, start=1):
        key = evidence_dedup_key(evidence)
        if key in seen:
            continue
        seen.add(key)
        display_rank = len(normalized) + 1
        evidence_id = _stable_evidence_id(evidence)
        normalized.append(
            replace(
                evidence,
                evidence_id=evidence_id,
                metadata={
                    **evidence.metadata,
                    "evidence_id": evidence_id,
                    "retrieval_rank": display_rank,
                    "raw_retrieval_rank": raw_rank,
                    "score_display": score_display(evidence.score),
                    "score_display_mode": (
                        "backend_score" if evidence.score is not None else "unavailable"
                    ),
                    "score_semantics": _score_semantics(evidence),
                    "dedup_key_type": key[0],
                },
            )
        )
        if limit is not None and len(normalized) >= limit:
            break

    return normalized


def evidence_dedup_key(evidence: Evidence) -> tuple[str, str]:
    evidence_id = _optional_str(evidence.evidence_id) or _optional_str(
        evidence.metadata.get("evidence_id")
    )
    if evidence_id:
        return ("evidence_id", evidence_id)

    source_type = _source_type(evidence)
    if source_type == "document_chunk":
        chunk_id = _optional_str(evidence.chunk_id)
        document_id = _optional_str(evidence.external_doc_id) or _optional_str(
            evidence.document_id
        )
        if document_id and chunk_id:
            return ("document_chunk", f"{document_id}:{chunk_id}")
        if chunk_id:
            return ("chunk_id", chunk_id)

    if source_type == "wiki_page":
        wiki_page_id = _optional_str(evidence.wiki_page_id) or _optional_str(
            evidence.metadata.get("wiki_page_id")
            or evidence.metadata.get("weknora_wiki_page_id")
            or evidence.metadata.get("slug")
        )
        if wiki_page_id:
            return ("wiki_page", wiki_page_id)

    stable_text = " ".join(evidence.text.split())[:160]
    return (
        "content",
        "|".join(
            [
                source_type,
                _optional_str(evidence.source) or "",
                _optional_str(evidence.title) or "",
                stable_text,
            ]
        ),
    )


def score_display(score: float | None) -> str:
    if score is None:
        return "Score unavailable"
    return f"Score {score:.2f}"


def _stable_evidence_id(evidence: Evidence) -> str | None:
    existing = _optional_str(evidence.evidence_id) or _optional_str(
        evidence.metadata.get("evidence_id")
    )
    if existing:
        return existing
    source_type = _source_type(evidence)
    if source_type == "document_chunk" and evidence.chunk_id:
        return f"document_chunk:{evidence.chunk_id}"
    if source_type == "wiki_page":
        wiki_page_id = _optional_str(evidence.wiki_page_id) or _optional_str(
            evidence.metadata.get("wiki_page_id")
            or evidence.metadata.get("weknora_wiki_page_id")
            or evidence.metadata.get("slug")
        )
        if wiki_page_id:
            return f"wiki_page:{wiki_page_id}"
    return None


def _score_semantics(evidence: Evidence) -> str:
    value = evidence.metadata.get("score_semantics")
    if value not in (None, ""):
        return str(value)
    if evidence.source == "weknora_api":
        return "weknora_backend_score"
    return "backend_score"


def _source_type(evidence: Evidence) -> str:
    raw = (
        evidence.source_type
        or evidence.metadata.get("citation_source_type")
        or evidence.metadata.get("source_type")
    )
    normalized = str(raw or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or "unknown"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
