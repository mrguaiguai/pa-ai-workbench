from dataclasses import dataclass

from agent.schemas import Citation


@dataclass(frozen=True)
class CitationCheckResult:
    valid: bool
    warnings: list[str]


class CitationChecker:
    def validate(self, citations: list[Citation]) -> CitationCheckResult:
        warnings: list[str] = []
        seen_keys: set[tuple[str | None, str | None, str]] = set()

        for index, citation in enumerate(citations, start=1):
            if not citation.title.strip():
                warnings.append(f"Citation {index} is missing a title.")
            if not citation.text.strip():
                warnings.append(f"Citation {index} is missing evidence text.")
            if not citation.source.strip():
                warnings.append(f"Citation {index} is missing a source.")
            if citation.score is not None and not 0 <= citation.score <= 1:
                warnings.append(f"Citation {index} has an out-of-range score.")

            key = (citation.document_id, citation.chunk_id, citation.text)
            if key in seen_keys:
                warnings.append(f"Citation {index} duplicates earlier evidence.")
            seen_keys.add(key)

        return CitationCheckResult(valid=not warnings, warnings=warnings)

