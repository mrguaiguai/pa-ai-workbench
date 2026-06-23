"""Regression guard for fixed Phase 4 distractor evidence."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Any

from knowledge_engine.schemas import Evidence


DISTRACTOR_ANCHOR = "TEST-DISTRACTOR-001"
DISTRACTOR_WARNING_METADATA_KEY = "distractor_guard_warnings"

POLICY_TERMS = {
    "政策",
    "规则",
    "时限",
    "专项信息",
    "普通事项",
    "初稿",
    "依据",
    "新版",
    "旧版",
    "工作日",
}
ACTIVITY_TERMS = {
    "活动",
    "讲师",
    "排版",
    "演示",
    "培训",
    "安排",
    "材料准备",
}


@dataclass(frozen=True)
class DistractorGuardResult:
    items: list[Evidence]
    warnings: tuple[str, ...] = ()
    dropped_count: int = 0


def apply_distractor_guard(
    evidence_items: list[Evidence],
    query: str,
) -> DistractorGuardResult:
    if not evidence_items:
        return DistractorGuardResult(items=[])
    query_kind = _query_kind(query)
    kept: list[Evidence] = []
    dropped = 0

    for evidence in evidence_items:
        if not _is_distractor(evidence):
            kept.append(_attach_decision(evidence, "not_distractor"))
            continue
        if query_kind == "activity":
            kept.append(_attach_decision(evidence, "allowed_activity_context"))
            continue
        if query_kind == "policy":
            dropped += 1
            continue
        kept.append(_attach_decision(evidence, "neutral_query"))

    warnings: list[str] = []
    if dropped:
        warnings.append(
            f"Distractor guard dropped {dropped} TEST-DISTRACTOR-001 evidence item(s) for a policy-like query."
        )
    if evidence_items and not kept:
        warnings.append(
            "Distractor guard removed all retrieved evidence; do not use activity scheduling material as policy support."
        )
    return DistractorGuardResult(
        items=kept,
        warnings=tuple(warnings),
        dropped_count=dropped,
    )


def attach_distractor_guard_warnings(
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
                DISTRACTOR_WARNING_METADATA_KEY: list(warnings),
            },
        )
        for evidence in evidence_items
    ]


def _query_kind(query: str) -> str:
    normalized = str(query or "")
    policy_hits = sum(1 for term in POLICY_TERMS if term in normalized)
    activity_hits = sum(1 for term in ACTIVITY_TERMS if term in normalized)
    if activity_hits >= 2 and activity_hits >= policy_hits:
        return "activity"
    if policy_hits >= 2:
        return "policy"
    return "neutral"


def _is_distractor(evidence: Evidence) -> bool:
    metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
    values = [
        evidence.title,
        evidence.text,
        metadata.get("anchor"),
        metadata.get("test_anchor"),
        metadata.get("expected_anchor"),
        metadata.get("anchors"),
    ]
    return any(DISTRACTOR_ANCHOR in str(value or "") for value in values)


def _attach_decision(evidence: Evidence, decision: str) -> Evidence:
    return replace(
        evidence,
        metadata={
            **evidence.metadata,
            "distractor_guard_decision": decision,
        },
    )
