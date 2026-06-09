from dataclasses import dataclass
from typing import Any

from agent.schemas import Citation
from knowledge_engine.schemas import Evidence


@dataclass(frozen=True)
class CitationCheckResult:
    valid: bool
    warnings: list[str]


@dataclass(frozen=True)
class _EvidenceRecord:
    evidence_id: str | None
    source_type: str
    document_id: str | None
    external_doc_id: str | None
    chunk_id: str | None
    wiki_page_id: str | None
    title: str
    text: str
    source: str
    metadata: dict[str, Any]


class CitationChecker:
    def validate(
        self,
        citations: list[Citation],
        evidence_items: list[Citation | Evidence] | None = None,
    ) -> CitationCheckResult:
        warnings: list[str] = []
        seen_keys: set[tuple[str | None, str | None, str | None, str]] = set()
        evidence_index = self._build_evidence_index(evidence_items)
        evidence_check_enabled = evidence_items is not None

        for index, citation in enumerate(citations, start=1):
            if not citation.title.strip():
                warnings.append(f"Citation {index} is missing a title.")
            if not citation.text.strip():
                warnings.append(f"Citation {index} is missing evidence text.")
            if not citation.source.strip():
                warnings.append(f"Citation {index} is missing a source.")
            if (
                citation.source != "weknora_api"
                and citation.score is not None
                and not 0 <= citation.score <= 1
            ):
                warnings.append(f"Citation {index} has an out-of-range score.")
            warnings.extend(self._traceability_warnings(index, citation))
            if evidence_check_enabled:
                warnings.extend(
                    self._real_evidence_warnings(index, citation, evidence_index)
                )

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
    def _real_evidence_warnings(
        cls,
        index: int,
        citation: Citation,
        evidence_index: dict[tuple[str, str], _EvidenceRecord],
    ) -> list[str]:
        if citation.source == "mock":
            return []

        evidence = cls._find_evidence(citation, evidence_index)
        if evidence is None:
            return [f"Citation {index} does not match retrieved evidence."]

        warnings: list[str] = []
        citation_source_type = cls._source_type(citation)
        if citation_source_type != evidence.source_type:
            warnings.append(f"Citation {index} source type does not match evidence.")
        if (
            citation.chunk_id
            and evidence.chunk_id
            and citation.chunk_id != evidence.chunk_id
        ):
            warnings.append(f"Citation {index} chunk id does not match evidence.")
        if (
            citation.document_id
            and evidence.document_id
            and citation.document_id != evidence.document_id
        ):
            warnings.append(f"Citation {index} document id does not match evidence.")
        if (
            citation.external_doc_id
            and evidence.external_doc_id
            and citation.external_doc_id != evidence.external_doc_id
        ):
            warnings.append(
                f"Citation {index} external document id does not match evidence."
            )

        citation_wiki_page_id = cls._wiki_page_id(citation)
        if (
            citation_wiki_page_id
            and evidence.wiki_page_id
            and citation_wiki_page_id != evidence.wiki_page_id
        ):
            warnings.append(f"Citation {index} wiki page id does not match evidence.")
        if not cls._text_matches(citation.text, evidence.text):
            warnings.append(f"Citation {index} text does not match evidence.")
        return warnings

    @classmethod
    def _traceability_warnings(cls, index: int, citation: Citation) -> list[str]:
        if citation.source == "mock":
            return []

        source_type = cls._source_type(citation)
        warnings: list[str] = []
        if not citation.evidence_id and not cls._binding_value(citation, "evidence_id"):
            warnings.append(f"Citation {index} is missing an evidence id.")
        if source_type == "unknown":
            warnings.append(f"Citation {index} is missing a source type.")
            return warnings
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

    @classmethod
    def _build_evidence_index(
        cls,
        evidence_items: list[Citation | Evidence] | None,
    ) -> dict[tuple[str, str], _EvidenceRecord]:
        index: dict[tuple[str, str], _EvidenceRecord] = {}
        for item in evidence_items or []:
            record = cls._to_evidence_record(item)
            for key in cls._record_keys(record):
                index.setdefault(key, record)
        return index

    @classmethod
    def _to_evidence_record(cls, item: Citation | Evidence) -> _EvidenceRecord:
        metadata = getattr(item, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
        source_type = cls._record_source_type(item, metadata)
        return _EvidenceRecord(
            evidence_id=cls._optional_str(
                getattr(item, "evidence_id", None)
                or cls._metadata_binding_value(metadata, "evidence_id")
                or metadata.get("evidence_id")
            ),
            source_type=source_type,
            document_id=cls._optional_str(getattr(item, "document_id", None)),
            external_doc_id=cls._optional_str(getattr(item, "external_doc_id", None)),
            chunk_id=cls._optional_str(getattr(item, "chunk_id", None)),
            wiki_page_id=cls._optional_str(
                getattr(item, "wiki_page_id", None)
                or cls._metadata_binding_value(metadata, "wiki_page_id")
                or metadata.get("wiki_page_id")
            ),
            title=str(getattr(item, "title", "") or ""),
            text=str(getattr(item, "text", "") or ""),
            source=str(getattr(item, "source", "") or ""),
            metadata=metadata,
        )

    @classmethod
    def _record_keys(cls, record: _EvidenceRecord) -> list[tuple[str, str]]:
        keys: list[tuple[str, str]] = []
        cls._append_key(keys, "evidence_id", record.evidence_id)
        if record.source_type == "document_chunk":
            cls._append_key(keys, "document_chunk", record.chunk_id)
            if record.document_id and record.chunk_id:
                keys.append(("document_chunk", f"{record.document_id}:{record.chunk_id}"))
            if record.external_doc_id and record.chunk_id:
                keys.append(
                    ("document_chunk", f"{record.external_doc_id}:{record.chunk_id}")
                )
        if record.source_type == "wiki_page":
            cls._append_key(keys, "wiki_page", record.wiki_page_id)
        return keys

    @classmethod
    def _find_evidence(
        cls,
        citation: Citation,
        evidence_index: dict[tuple[str, str], _EvidenceRecord],
    ) -> _EvidenceRecord | None:
        for key in cls._citation_keys(citation):
            evidence = evidence_index.get(key)
            if evidence is not None:
                return evidence
        return None

    @classmethod
    def _citation_keys(cls, citation: Citation) -> list[tuple[str, str]]:
        keys: list[tuple[str, str]] = []
        cls._append_key(
            keys,
            "evidence_id",
            citation.evidence_id
            or cls._binding_value(citation, "evidence_id")
            or citation.metadata.get("evidence_id"),
        )
        source_type = cls._source_type(citation)
        if source_type == "document_chunk":
            cls._append_key(keys, "document_chunk", citation.chunk_id)
            if citation.document_id and citation.chunk_id:
                keys.append(
                    ("document_chunk", f"{citation.document_id}:{citation.chunk_id}")
                )
            if citation.external_doc_id and citation.chunk_id:
                keys.append(
                    ("document_chunk", f"{citation.external_doc_id}:{citation.chunk_id}")
                )
        if source_type == "wiki_page":
            cls._append_key(keys, "wiki_page", cls._wiki_page_id(citation))
        return keys

    @classmethod
    def _record_source_type(
        cls,
        item: Citation | Evidence,
        metadata: dict[str, Any],
    ) -> str:
        raw = (
            getattr(item, "source_type", None)
            or cls._metadata_binding_value(metadata, "source_type")
            or metadata.get("citation_source_type")
            or metadata.get("source_type")
        )
        return cls._normalize_source_type(raw)

    @classmethod
    def _wiki_page_id(cls, citation: Citation) -> str | None:
        return cls._optional_str(
            citation.wiki_page_id
            or cls._binding_value(citation, "wiki_page_id")
            or citation.metadata.get("wiki_page_id")
        )

    @classmethod
    def _normalize_source_type(cls, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"document", "document_chunk", "chunk"}:
            return "document_chunk"
        if normalized in {"wiki", "wiki_page", "wiki-page"}:
            return "wiki_page"
        return normalized or "unknown"

    @staticmethod
    def _metadata_binding_value(metadata: dict[str, Any], key: str) -> Any:
        binding = metadata.get("citation_binding")
        if isinstance(binding, dict):
            return binding.get(key)
        return None

    @classmethod
    def _append_key(
        cls,
        keys: list[tuple[str, str]],
        kind: str,
        value: Any,
    ) -> None:
        normalized = cls._optional_str(value)
        if normalized:
            keys.append((kind, normalized))

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _text_matches(citation_text: str, evidence_text: str) -> bool:
        citation_normalized = " ".join(citation_text.split())
        evidence_normalized = " ".join(evidence_text.split())
        if not citation_normalized or not evidence_normalized:
            return False
        return (
            citation_normalized in evidence_normalized
            or evidence_normalized in citation_normalized
        )
