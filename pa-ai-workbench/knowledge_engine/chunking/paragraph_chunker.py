from dataclasses import dataclass
import re

from knowledge_engine.chunking.base import Chunker
from knowledge_engine.chunking.schemas import ChunkingConfig
from knowledge_engine.chunking.schemas import DocumentChunkCandidate
from knowledge_engine.chunking.schemas import content_hash
from knowledge_engine.chunking.schemas import estimate_token_count
from knowledge_engine.parsers.schemas import ParsedDocument
from knowledge_engine.parsers.schemas import ParsedSection


@dataclass(frozen=True)
class _ParagraphUnit:
    text: str
    start_char: int
    end_char: int
    title: str | None
    page_number: int | None
    section_path: list[str]
    section_index: int
    paragraph_index: int
    metadata: dict


@dataclass(frozen=True)
class _ChunkSpan:
    start_char: int
    end_char: int
    title: str | None
    page_number: int | None
    section_path: list[str]
    paragraph_start_index: int | None
    paragraph_end_index: int | None
    metadata: dict


class ParagraphChunker(Chunker):
    PARAGRAPH_SEPARATOR = re.compile(r"\n[ \t]*\n+")

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def chunk(self, document: ParsedDocument) -> list[DocumentChunkCandidate]:
        units = self._paragraph_units(document)
        if not units and document.text:
            units = [
                _ParagraphUnit(
                    text=document.text.strip(),
                    start_char=0,
                    end_char=len(document.text),
                    title=document.title,
                    page_number=None,
                    section_path=[],
                    section_index=0,
                    paragraph_index=0,
                    metadata={"fallback": "whole_document"},
                )
            ]
        spans = self._build_spans(units)
        return [
            self._build_chunk(document=document, span=span, chunk_index=index)
            for index, span in enumerate(spans)
        ]

    def _paragraph_units(self, document: ParsedDocument) -> list[_ParagraphUnit]:
        units: list[_ParagraphUnit] = []
        paragraph_index = 0
        for section_index, section in enumerate(document.sections):
            for paragraph_text, start_char, end_char in self._section_paragraphs(section):
                units.append(
                    _ParagraphUnit(
                        text=paragraph_text,
                        start_char=start_char,
                        end_char=end_char,
                        title=section.title,
                        page_number=section.page_number,
                        section_path=list(section.section_path),
                        section_index=section_index,
                        paragraph_index=paragraph_index,
                        metadata={
                            "section_index": section_index,
                            "section_start_char": section.start_char,
                            "section_end_char": section.end_char,
                        },
                    )
                )
                paragraph_index += 1
        return units

    def _section_paragraphs(self, section: ParsedSection) -> list[tuple[str, int, int]]:
        text = section.text
        if not text:
            return []

        paragraphs: list[tuple[str, int, int]] = []
        cursor = 0
        for separator in self.PARAGRAPH_SEPARATOR.finditer(text):
            self._append_paragraph(
                paragraphs=paragraphs,
                raw=text[cursor : separator.start()],
                raw_start=cursor,
                section_start=section.start_char,
            )
            cursor = separator.end()
        self._append_paragraph(
            paragraphs=paragraphs,
            raw=text[cursor:],
            raw_start=cursor,
            section_start=section.start_char,
        )
        return paragraphs

    @staticmethod
    def _append_paragraph(
        paragraphs: list[tuple[str, int, int]],
        raw: str,
        raw_start: int,
        section_start: int,
    ) -> None:
        if not raw.strip():
            return
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        start_char = section_start + raw_start + leading
        end_char = section_start + raw_start + trailing
        paragraphs.append((raw.strip(), start_char, end_char))

    def _build_spans(self, units: list[_ParagraphUnit]) -> list[_ChunkSpan]:
        spans: list[_ChunkSpan] = []
        current: list[_ParagraphUnit] = []

        def flush() -> None:
            nonlocal current
            if not current:
                return
            spans.append(self._span_from_units(current))
            current = []

        for unit in units:
            unit_span_chars = unit.end_char - unit.start_char
            if unit_span_chars > self.config.max_chars:
                flush()
                spans.extend(self._split_long_unit(unit))
                continue

            if not current:
                current = [unit]
                continue

            proposed_start = current[0].start_char
            proposed_end = unit.end_char
            proposed_chars = proposed_end - proposed_start
            if proposed_chars <= self.config.max_chars:
                current.append(unit)
                continue

            flush()
            current = [unit]

        flush()
        return self._merge_small_tail_spans(spans)

    def _split_long_unit(self, unit: _ParagraphUnit) -> list[_ChunkSpan]:
        spans: list[_ChunkSpan] = []
        start = unit.start_char
        end = unit.end_char
        window_start = start
        part_index = 0
        while window_start < end:
            window_end = min(end, window_start + self.config.max_chars)
            spans.append(
                _ChunkSpan(
                    start_char=window_start,
                    end_char=window_end,
                    title=unit.title,
                    page_number=unit.page_number,
                    section_path=list(unit.section_path),
                    paragraph_start_index=unit.paragraph_index,
                    paragraph_end_index=unit.paragraph_index,
                    metadata={
                        **unit.metadata,
                        "split_from_long_paragraph": True,
                        "long_paragraph_part": part_index,
                    },
                )
            )
            if window_end >= end:
                break
            next_start = max(window_end - self.config.overlap_chars, window_start + 1)
            window_start = next_start
            part_index += 1
        return spans

    def _merge_small_tail_spans(self, spans: list[_ChunkSpan]) -> list[_ChunkSpan]:
        if len(spans) < 2 or self.config.min_chars <= 0:
            return spans

        merged: list[_ChunkSpan] = []
        for span in spans:
            if (
                merged
                and span.end_char - span.start_char < self.config.min_chars
                and span.end_char - merged[-1].start_char <= self.config.max_chars
            ):
                previous = merged.pop()
                merged.append(self._merge_spans(previous, span))
            else:
                merged.append(span)
        return merged

    @staticmethod
    def _span_from_units(units: list[_ParagraphUnit]) -> _ChunkSpan:
        first = units[0]
        last = units[-1]
        return _ChunkSpan(
            start_char=first.start_char,
            end_char=last.end_char,
            title=first.title or last.title,
            page_number=first.page_number,
            section_path=list(first.section_path or last.section_path),
            paragraph_start_index=first.paragraph_index,
            paragraph_end_index=last.paragraph_index,
            metadata={
                "section_index": first.section_index,
                "paragraph_count": len(units),
            },
        )

    @staticmethod
    def _merge_spans(left: _ChunkSpan, right: _ChunkSpan) -> _ChunkSpan:
        return _ChunkSpan(
            start_char=left.start_char,
            end_char=right.end_char,
            title=left.title or right.title,
            page_number=left.page_number or right.page_number,
            section_path=list(left.section_path or right.section_path),
            paragraph_start_index=left.paragraph_start_index,
            paragraph_end_index=right.paragraph_end_index,
            metadata={
                **left.metadata,
                "merged_small_tail": True,
                "right_metadata": right.metadata,
            },
        )

    def _build_chunk(
        self,
        document: ParsedDocument,
        span: _ChunkSpan,
        chunk_index: int,
    ) -> DocumentChunkCandidate:
        start_char = self._apply_overlap_start(document.text, span, chunk_index)
        content, content_start, content_end = self._content_for_span(
            document.text,
            start_char,
            span.end_char,
        )
        title = span.title or document.title
        metadata = {
            **span.metadata,
            "document_title": document.title,
            "chunker": "paragraph",
            "max_chars": self.config.max_chars,
            "overlap_chars": self.config.overlap_chars,
            "min_chars": self.config.min_chars,
        }
        if content_start < span.start_char:
            metadata["overlap_applied"] = True
            metadata["logical_start_char"] = span.start_char

        return DocumentChunkCandidate(
            chunk_index=chunk_index,
            title=title,
            content=content,
            content_hash=content_hash(content),
            token_count=estimate_token_count(content),
            char_count=len(content),
            start_char=content_start,
            end_char=content_end,
            page_number=span.page_number,
            section_path=list(span.section_path),
            paragraph_start_index=span.paragraph_start_index,
            paragraph_end_index=span.paragraph_end_index,
            source_path=document.source_path,
            file_name=document.file_name,
            file_type=document.file_type,
            metadata=metadata,
        )

    def _apply_overlap_start(
        self,
        document_text: str,
        span: _ChunkSpan,
        chunk_index: int,
    ) -> int:
        if chunk_index == 0 or self.config.overlap_chars <= 0:
            return span.start_char
        base_chars = span.end_char - span.start_char
        overlap_budget = min(self.config.overlap_chars, self.config.max_chars - base_chars)
        if overlap_budget <= 0:
            return span.start_char
        candidate = max(0, span.start_char - overlap_budget)
        while candidate < span.start_char and document_text[candidate].isspace():
            candidate += 1
        return candidate

    @staticmethod
    def _content_for_span(
        document_text: str,
        start_char: int,
        end_char: int,
    ) -> tuple[str, int, int]:
        raw = document_text[start_char:end_char]
        if not raw:
            return "", start_char, end_char
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        content_start = start_char + leading
        content_end = start_char + trailing
        return raw.strip(), content_start, content_end
