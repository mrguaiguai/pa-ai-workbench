from __future__ import annotations

from dataclasses import dataclass
import re

from agent.schemas import Citation


_CITATION_REF_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class FaithfulnessCheckResult:
    valid: bool
    warnings: list[str]
    warning_codes: list[str]
    citation_coverage: float
    missing_citation_terms: list[str]
    omitted_required_terms: list[str]
    unsupported_claims: list[str]
    invalid_citation_refs: list[str]


class FaithfulnessChecker:
    """Lightweight deterministic Agent-output regression checker.

    This is not a semantic truth engine. It checks explicit golden-set facts,
    citation references, and unsupported-claim sentinels so prompt/model changes
    cannot silently remove the basic PA evidence contract.
    """

    def validate(
        self,
        markdown: str,
        citations: list[Citation],
        *,
        required_terms: list[str] | None = None,
        unsupported_terms: list[str] | None = None,
        require_no_evidence_warning: bool = False,
    ) -> FaithfulnessCheckResult:
        text = markdown or ""
        warnings: list[str] = []
        warning_codes: list[str] = []
        invalid_refs = self._invalid_citation_refs(text, citations)
        if invalid_refs:
            warnings.append(
                "INVALID_CITATION_REF: Output references unavailable citation numbers."
            )
            _append_code(warning_codes, "INVALID_CITATION_REF")

        omitted_terms, missing_citation_terms = self._required_term_findings(
            text,
            required_terms or [],
        )
        if omitted_terms:
            warnings.append(
                "REQUIRED_FACT_OMITTED: Output omitted required golden-set facts."
            )
            _append_code(warning_codes, "REQUIRED_FACT_OMITTED")
        if missing_citation_terms:
            warnings.append(
                "MISSING_CITATION: Required facts appear without a numbered citation."
            )
            _append_code(warning_codes, "MISSING_CITATION")

        unsupported_claims = self._unsupported_claims(
            text,
            citations,
            unsupported_terms or [],
        )
        if unsupported_claims:
            warnings.append(
                "UNSUPPORTED_CLAIM: Output includes claims not present in retrieved evidence."
            )
            _append_code(warning_codes, "UNSUPPORTED_CLAIM")

        if require_no_evidence_warning:
            has_warning = _has_no_evidence_warning(text)
            has_citation_refs = bool(_CITATION_REF_PATTERN.search(text))
            if not has_warning or has_citation_refs or citations:
                warnings.append(
                    "NO_EVIDENCE_WARNING_MISSING: No-evidence output must warn and avoid citations."
                )
                _append_code(warning_codes, "NO_EVIDENCE_WARNING_MISSING")

        required_count = len(required_terms or [])
        covered_count = required_count - len(omitted_terms) - len(missing_citation_terms)
        citation_coverage = 1.0 if required_count == 0 else max(covered_count, 0) / required_count

        return FaithfulnessCheckResult(
            valid=not warnings,
            warnings=warnings,
            warning_codes=warning_codes,
            citation_coverage=citation_coverage,
            missing_citation_terms=missing_citation_terms,
            omitted_required_terms=omitted_terms,
            unsupported_claims=unsupported_claims,
            invalid_citation_refs=invalid_refs,
        )

    @staticmethod
    def _invalid_citation_refs(markdown: str, citations: list[Citation]) -> list[str]:
        max_ref = len(citations)
        invalid: list[str] = []
        for match in _CITATION_REF_PATTERN.finditer(markdown):
            ref = int(match.group(1))
            if ref < 1 or ref > max_ref:
                invalid.append(match.group(0))
        return sorted(set(invalid))

    @staticmethod
    def _required_term_findings(
        markdown: str,
        required_terms: list[str],
    ) -> tuple[list[str], list[str]]:
        omitted: list[str] = []
        missing_citation: list[str] = []
        segments = _segments(markdown)
        for term in required_terms:
            normalized = term.strip()
            if not normalized:
                continue
            matching_segments = [
                segment
                for segment in segments
                if normalized.lower() in segment.lower()
            ]
            if not matching_segments:
                omitted.append(normalized)
                continue
            if not any(_CITATION_REF_PATTERN.search(segment) for segment in matching_segments):
                missing_citation.append(normalized)
        return omitted, missing_citation

    @staticmethod
    def _unsupported_claims(
        markdown: str,
        citations: list[Citation],
        unsupported_terms: list[str],
    ) -> list[str]:
        output = markdown.lower()
        evidence_text = " ".join(
            f"{citation.title} {citation.text}" for citation in citations
        ).lower()
        claims: list[str] = []
        for term in unsupported_terms:
            normalized = term.strip()
            if not normalized:
                continue
            needle = normalized.lower()
            if needle in output and needle not in evidence_text:
                claims.append(normalized)
        return claims


def _segments(markdown: str) -> list[str]:
    candidates: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        candidates.extend(part.strip() for part in re.split(r"[。.!?；;]", stripped))
    return [candidate for candidate in candidates if candidate]


def _has_no_evidence_warning(markdown: str) -> bool:
    normalized = markdown.lower()
    return "依据不足" in markdown or "no_evidence" in normalized or "no evidence" in normalized


def _append_code(codes: list[str], code: str) -> None:
    if code not in codes:
        codes.append(code)
