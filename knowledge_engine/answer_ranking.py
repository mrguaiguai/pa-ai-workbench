"""PA-side answer-bearing evidence ranking and diagnostics."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from knowledge_engine.schemas import Evidence


MAX_MATCHED_TERMS = 12
CJK_MIN_TERM_LEN = 2
CJK_MAX_TERM_LEN = 6
TERM_LIMIT = 180
STOP_TERMS = {
    "什么",
    "哪些",
    "哪个",
    "多少",
    "几个",
    "如何",
    "是否",
    "应该",
    "需要",
    "以及",
    "还是",
    "为什么",
    "是什么",
}


def rank_answer_bearing_evidence(
    evidence_items: list[Evidence],
    query: str,
) -> list[Evidence]:
    """Rank likely answer-bearing chunks ahead of broad but less useful hits."""

    terms = _query_terms(query)
    if not evidence_items or not terms:
        return [
            _attach_ranking_metadata(
                evidence=evidence,
                raw_rank=index + 1,
                rerank_rank=index + 1,
                score=0.0,
                matched_terms=[],
                matched_metadata=[],
            )
            for index, evidence in enumerate(evidence_items)
        ]

    scored: list[tuple[float, int, Evidence, list[str], list[str]]] = []
    for raw_index, evidence in enumerate(evidence_items, start=1):
        score, matched_terms, matched_metadata = _answer_score(evidence, terms)
        scored.append((score, raw_index, evidence, matched_terms, matched_metadata))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        _attach_ranking_metadata(
            evidence=evidence,
            raw_rank=raw_rank,
            rerank_rank=rerank_rank,
            score=score,
            matched_terms=matched_terms,
            matched_metadata=matched_metadata,
        )
        for rerank_rank, (score, raw_rank, evidence, matched_terms, matched_metadata)
        in enumerate(scored, start=1)
    ]


def _answer_score(
    evidence: Evidence,
    terms: list[str],
) -> tuple[float, list[str], list[str]]:
    title = _normalize_text(evidence.title)
    text = _normalize_text(evidence.text)
    metadata_terms = _metadata_terms(evidence.metadata)

    matched_title = [term for term in terms if term in title]
    matched_text = [term for term in terms if term in text]
    matched_metadata = [
        term
        for term in terms
        if any(term in metadata_value for metadata_value in metadata_terms)
    ]
    text_only_matches = [term for term in matched_text if term not in matched_title]
    unique_matches = _unique(
        [*text_only_matches, *matched_text, *matched_title, *matched_metadata]
    )
    score = (
        len(matched_title) * 2.0
        + len(matched_text) * 1.0
        + len(matched_metadata) * 1.5
        + _numeric_overlap_bonus(evidence, terms)
    )
    coverage = len(unique_matches) / max(len(terms), 1)
    score += coverage * 4.0
    return (
        round(score, 4),
        unique_matches[:MAX_MATCHED_TERMS],
        _unique(matched_metadata)[:MAX_MATCHED_TERMS],
    )


def _attach_ranking_metadata(
    *,
    evidence: Evidence,
    raw_rank: int,
    rerank_rank: int,
    score: float,
    matched_terms: list[str],
    matched_metadata: list[str],
) -> Evidence:
    metadata = {
        **evidence.metadata,
        "answer_bearing_score": score,
        "answer_bearing_raw_rank": raw_rank,
        "answer_bearing_rank": rerank_rank,
        "answer_bearing_rank_delta": raw_rank - rerank_rank,
        "answer_bearing_matched_terms": matched_terms,
        "answer_bearing_matched_metadata": matched_metadata,
        "answer_bearing_strategy": "query_term_overlap",
    }
    return replace(evidence, metadata=metadata)


def _query_terms(query: str) -> list[str]:
    normalized = _normalize_text(query)
    if not normalized:
        return []
    terms: list[str] = []
    terms.extend(
        match.group(0)
        for match in re.finditer(r"[a-z0-9_]{2,}", normalized)
    )
    terms.extend(_cjk_terms(normalized))
    return _unique(
        term
        for term in sorted(terms, key=lambda item: (-len(item), item))
        if len(term) >= CJK_MIN_TERM_LEN and term not in STOP_TERMS
    )[:TERM_LIMIT]


def _cjk_terms(value: str) -> list[str]:
    terms: list[str] = []
    for match in re.finditer(r"[\u4e00-\u9fff]{2,}", value):
        segment = match.group(0)
        if len(segment) <= CJK_MAX_TERM_LEN:
            terms.append(segment)
            continue
        for size in range(CJK_MIN_TERM_LEN, CJK_MAX_TERM_LEN + 1):
            terms.extend(
                segment[index : index + size]
                for index in range(0, len(segment) - size + 1)
            )
    return terms


def _metadata_terms(metadata: dict[str, Any]) -> list[str]:
    safe_keys = {
        "anchor",
        "anchors",
        "business_area",
        "document_type",
        "file_name",
        "source_type",
        "title",
        "weknora_chunk_type",
        "weknora_match_type",
    }
    values: list[str] = []
    for key, value in metadata.items():
        if str(key) not in safe_keys:
            continue
        values.extend(_flatten_metadata_value(value))
    return [_normalize_text(value) for value in values if _normalize_text(value)]


def _flatten_metadata_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            result.extend(_flatten_metadata_value(item))
        return result
    return []


def _numeric_overlap_bonus(evidence: Evidence, terms: list[str]) -> float:
    query_numbers = {
        term
        for term in terms
        if re.search(r"\d", term)
        or any(unit in term for unit in ("一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "百"))
    }
    if not query_numbers:
        return 0.0
    haystack = _normalize_text(f"{evidence.title} {evidence.text}")
    return sum(1.0 for term in query_numbers if term in haystack)


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
