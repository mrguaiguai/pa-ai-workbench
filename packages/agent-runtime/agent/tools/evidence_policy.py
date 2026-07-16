from dataclasses import dataclass
from typing import Any

from agent.schemas import Citation
from agent.tools.citation_checker import CitationChecker


WEAK_EVIDENCE_SCORE_THRESHOLD = 0.35


@dataclass(frozen=True)
class EvidencePolicyResult:
    citations: list[Citation]
    warnings: list[str]
    warning_codes: list[str]
    weak_evidence_count: int
    dropped_citation_count: int
    source_type_mismatch_count: int
    evidence_mode: str


class EvidencePolicy:
    def __init__(
        self,
        citation_checker: CitationChecker | None = None,
        weak_score_threshold: float = WEAK_EVIDENCE_SCORE_THRESHOLD,
    ) -> None:
        self.citation_checker = citation_checker or CitationChecker()
        self.weak_score_threshold = weak_score_threshold

    def evaluate(
        self,
        citations: list[Citation],
        *,
        workflow: str,
        expected_source_type: str | None = None,
        expected_source_types: list[str] | tuple[str, ...] | None = None,
        require_all_expected_source_types: bool = False,
    ) -> EvidencePolicyResult:
        warnings: list[str] = []
        warning_codes: list[str] = []
        accepted: list[Citation] = []
        dropped_count = 0
        mismatch_count = 0

        normalized_expected_types = _normalize_source_types(
            [*(expected_source_types or []), *([expected_source_type] if expected_source_type else [])]
        )
        for citation in citations:
            source_type = _citation_source_type(citation)
            if normalized_expected_types and source_type not in normalized_expected_types:
                mismatch_count += 1
                dropped_count += 1
                continue
            check = self.citation_checker.validate([citation], evidence_items=[citation])
            if not check.valid:
                dropped_count += 1
                warnings.extend(
                    f"CITATION_DROPPED: {warning}" for warning in check.warnings
                )
                _append_code(warning_codes, "CITATION_DROPPED")
                continue
            accepted.append(citation)

        if mismatch_count:
            warnings.append(
                "SOURCE_TYPE_MISMATCH: Retrieved evidence did not match the required "
                f"source_type={','.join(normalized_expected_types)}."
            )
            _append_code(warning_codes, "SOURCE_TYPE_MISMATCH")

        if require_all_expected_source_types and normalized_expected_types:
            accepted_types = {_citation_source_type(citation) for citation in accepted}
            missing_types = [
                source_type
                for source_type in normalized_expected_types
                if source_type not in accepted_types
            ]
            if missing_types:
                warnings.append(
                    "MISSING_SOURCE_TYPE: Required evidence source_type missing from "
                    f"citations: {','.join(missing_types)}."
                )
                _append_code(warning_codes, "MISSING_SOURCE_TYPE")

        if not accepted:
            warnings.append(f"NO_EVIDENCE: No evidence was found for {workflow}.")
            _append_code(warning_codes, "NO_EVIDENCE")

        weak_count = sum(
            1
            for citation in accepted
            if citation.score is not None and citation.score < self.weak_score_threshold
        )
        if weak_count:
            warnings.append(
                "WEAK_EVIDENCE: Some retrieved evidence has low confidence; "
                "treat conclusions as uncertain."
            )
            _append_code(warning_codes, "WEAK_EVIDENCE")

        return EvidencePolicyResult(
            citations=accepted,
            warnings=warnings,
            warning_codes=warning_codes,
            weak_evidence_count=weak_count,
            dropped_citation_count=dropped_count,
            source_type_mismatch_count=mismatch_count,
            evidence_mode=_evidence_mode(accepted),
        )


def _citation_source_type(citation: Citation) -> str:
    return _normalize_source_type(
        citation.source_type
        or _binding_value(citation.metadata, "source_type")
        or citation.metadata.get("citation_source_type")
        or citation.metadata.get("source_type")
    ) or "unknown"


def _normalize_source_type(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or None


def _normalize_source_types(values: list[object]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        source_type = _normalize_source_type(value)
        if not source_type or source_type in normalized:
            continue
        normalized.append(source_type)
    return normalized


def _binding_value(metadata: dict[str, Any], key: str) -> Any:
    binding = metadata.get("citation_binding")
    if isinstance(binding, dict):
        return binding.get(key)
    return None


def _append_code(codes: list[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _evidence_mode(citations: list[Citation]) -> str:
    if not citations:
        return "no_evidence"
    if all(citation.source == "weknora_api" for citation in citations):
        return "weknora_api"
    if all(citation.source == "mock" for citation in citations):
        return "mock"
    return "mixed"
