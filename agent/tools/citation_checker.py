from dataclasses import dataclass
from typing import Any

from agent.schemas import Citation


@dataclass(frozen=True)
class CitationCheckResult:
    valid: bool
    warnings: list[str]


class CitationChecker:
    def validate(self, citations: list[Citation]) -> CitationCheckResult:
        warnings: list[str] = []
        seen_keys: set[tuple[str | None, str | None, str | None, str]] = set()

        for index, citation in enumerate(citations, start=1):
            if not citation.title.strip():
                warnings.append(f"Citation {index} is missing a title.")
            if not citation.text.strip():
                warnings.append(f"Citation {index} is missing evidence text.")
            if not citation.source.strip():
                warnings.append(f"Citation {index} is missing a source.")
            if citation.score is not None and not 0 <= citation.score <= 1:
                warnings.append(f"Citation {index} has an out-of-range score.")
            warnings.extend(self._traceability_warnings(index, citation))

            key = (
                citation.evidence_id,
                citation.document_id,
                citation.chunk_id,
                citation.text,
            )
            if key in seen_keys:
                warnings.append(f"Citation {index} duplicates earlier evidence.")
            seen_keys.add(key)

        return CitationCheckResult(valid=not warnings, warnings=warnings)

    @classmethod
    def _traceability_warnings(cls, index: int, citation: Citation) -> list[str]:
        if citation.source == "mock":
            return []

        source_type = cls._source_type(citation)
        warnings: list[str] = []
        if not citation.evidence_id and not cls._binding_value(citation, "evidence_id"):
            warnings.append(f"Citation {index} is missing an evidence id.")
        if source_type == "document_chunk":
            if not citation.chunk_id:
                warnings.append(f"Citation {index} is missing a chunk id.")
            if not citation.document_id and not citation.external_doc_id:
                warnings.append(f"Citation {index} is missing a document id.")
        elif source_type == "wiki_page":
            if not citation.wiki_page_id and not cls._binding_value(
                citation, "wiki_page_id"
            ):
                warnings.append(f"Citation {index} is missing a wiki page id.")
        else:
            warnings.append(f"Citation {index} has an unknown source type.")
        return warnings

    @classmethod
    def _source_type(cls, citation: Citation) -> str:
        raw = (
            citation.source_type
            or cls._binding_value(citation, "source_type")
            or citation.metadata.get("citation_source_type")
            or citation.metadata.get("source_type")
        )
        normalized = str(raw or "").strip().lower()
        if normalized in {"document", "document_chunk", "chunk"}:
            return "document_chunk"
        if normalized in {"wiki", "wiki_page", "wiki-page"}:
            return "wiki_page"
        return normalized or "unknown"

    @staticmethod
    def _binding_value(citation: Citation, key: str) -> Any:
        binding = citation.metadata.get("citation_binding")
        if isinstance(binding, dict):
            return binding.get(key)
        return None
