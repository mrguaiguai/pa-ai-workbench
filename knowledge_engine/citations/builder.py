from dataclasses import asdict
from typing import Any

from knowledge_engine.citations.schemas import CitationBinding
from knowledge_engine.schemas import Evidence


class CitationBindingError(ValueError):
    pass


class CitationBuilder:
    def build(self, evidence: Evidence) -> Evidence:
        binding = self._binding_for_evidence(evidence)
        metadata = {
            **evidence.metadata,
            "citation_bound": True,
            "citation_binding": asdict(binding),
        }
        metadata["citation_source_type"] = binding.source_type
        metadata["evidence_id"] = binding.evidence_id
        return Evidence(
            document_id=evidence.document_id,
            external_doc_id=evidence.external_doc_id,
            chunk_id=evidence.chunk_id,
            title=evidence.title,
            text=evidence.text,
            score=evidence.score,
            source=evidence.source,
            metadata=metadata,
            evidence_id=binding.evidence_id,
            source_type=binding.source_type,
            wiki_page_id=binding.wiki_page_id,
        )

    def build_many(self, evidence_items: list[Evidence]) -> list[Evidence]:
        bound: list[Evidence] = []
        for evidence in evidence_items:
            try:
                bound.append(self.build(evidence))
            except CitationBindingError:
                continue
        return bound

    def _binding_for_evidence(self, evidence: Evidence) -> CitationBinding:
        source_type = self._source_type(evidence)
        evidence_id = self._evidence_id(evidence, source_type)
        self._validate_traceability(evidence, source_type, evidence_id)
        wiki_page_id = self._wiki_page_id(evidence)
        return CitationBinding(
            evidence_id=evidence_id,
            source_type=source_type,
            document_id=evidence.document_id,
            external_doc_id=evidence.external_doc_id,
            chunk_id=evidence.chunk_id,
            wiki_page_id=wiki_page_id,
            title=evidence.title,
            text=evidence.text,
            score=evidence.score,
            metadata=self._binding_metadata(evidence),
        )

    @classmethod
    def _source_type(cls, evidence: Evidence) -> str:
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

    @classmethod
    def _evidence_id(cls, evidence: Evidence, source_type: str) -> str:
        existing = cls._optional_str(evidence.evidence_id) or cls._optional_str(
            evidence.metadata.get("evidence_id")
        )
        if existing:
            return existing
        if source_type == "document_chunk" and evidence.chunk_id:
            return f"document_chunk:{evidence.chunk_id}"
        if source_type == "wiki_page":
            wiki_page_id = cls._wiki_page_id(evidence)
            if wiki_page_id:
                return f"wiki_page:{wiki_page_id}"
        raise CitationBindingError("Evidence has no stable citation id.")

    @classmethod
    def _validate_traceability(
        cls,
        evidence: Evidence,
        source_type: str,
        evidence_id: str,
    ) -> None:
        if not evidence.title.strip():
            raise CitationBindingError("Evidence title is required for citation.")
        if not evidence.text.strip():
            raise CitationBindingError("Evidence text is required for citation.")
        if not evidence_id:
            raise CitationBindingError("Evidence id is required for citation.")
        if source_type == "document_chunk":
            if not evidence.chunk_id:
                raise CitationBindingError("Document citation must include chunk_id.")
            if not evidence.document_id and not evidence.external_doc_id:
                raise CitationBindingError(
                    "Document citation must include a document id."
                )
            return
        if source_type == "wiki_page":
            if not cls._wiki_page_id(evidence):
                raise CitationBindingError("Wiki citation must include wiki_page_id.")
            return
        raise CitationBindingError(f"Unsupported citation source_type: {source_type}")

    @classmethod
    def _binding_metadata(cls, evidence: Evidence) -> dict[str, Any]:
        return {
            "source": evidence.source,
            "evidence_id": evidence.evidence_id,
            "source_type": evidence.source_type,
            "chunk_index": evidence.metadata.get("chunk_index"),
            "page_number": evidence.metadata.get("page_number"),
            "section_path": evidence.metadata.get("section_path"),
            "start_char": evidence.metadata.get("start_char"),
            "end_char": evidence.metadata.get("end_char"),
            "business_area": evidence.metadata.get("business_area"),
            "document_type": evidence.metadata.get("document_type"),
            "wiki_page_id": cls._wiki_page_id(evidence),
            "wiki_slug": cls._wiki_slug(evidence),
            "weknora_wiki_page_id": cls._optional_str(
                evidence.metadata.get("weknora_wiki_page_id")
            ),
            "weknora_wiki_page_slug": cls._optional_str(
                evidence.metadata.get("weknora_wiki_page_slug")
            ),
        }

    @classmethod
    def _wiki_page_id(cls, evidence: Evidence) -> str | None:
        return cls._first_optional_str(
            evidence.wiki_page_id,
            evidence.metadata.get("wiki_page_id"),
            evidence.metadata.get("weknora_wiki_page_id"),
            evidence.metadata.get("pa_wiki_page_id"),
            evidence.metadata.get("id"),
        )

    @classmethod
    def _wiki_slug(cls, evidence: Evidence) -> str | None:
        return cls._first_optional_str(
            evidence.metadata.get("wiki_slug"),
            evidence.metadata.get("weknora_wiki_page_slug"),
            evidence.metadata.get("weknora_slug"),
            evidence.metadata.get("slug"),
            evidence.metadata.get("page_slug"),
        )

    @classmethod
    def _first_optional_str(cls, *values: Any) -> str | None:
        for value in values:
            normalized = cls._optional_str(value)
            if normalized:
                return normalized
        return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value)
        return text or None
