from datetime import datetime
import json
from typing import Any

from sqlmodel import Session
from sqlmodel import select

from app.models import Citation
from app.models import GeneratedOutput
from app.models import GenerationTask


def create_task(
    session: Session,
    task_type: str,
    title: str | None = None,
    conversation_id: str | None = None,
    input_json: str | None = None,
    status: str = "created",
    current_step: str | None = None,
    progress: int = 0,
    error_message: str | None = None,
) -> GenerationTask:
    task = GenerationTask(
        conversation_id=conversation_id,
        task_type=task_type,
        title=title,
        input_json=input_json,
        status=status,
        current_step=current_step,
        progress=progress,
        error_message=error_message,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def update_task_status(
    session: Session,
    task: GenerationTask,
    status: str,
    current_step: str | None = None,
    progress: int | None = None,
    error_message: str | None = None,
) -> GenerationTask:
    task.status = status
    task.current_step = current_step
    if progress is not None:
        task.progress = progress
    task.error_message = error_message
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def create_output(
    session: Session,
    task: GenerationTask,
    title: str,
    content_json: str | None = None,
    content_markdown: str | None = None,
    warnings_json: str | None = None,
    status: str = "completed",
) -> GeneratedOutput:
    output = GeneratedOutput(
        task_id=task.id,
        conversation_id=task.conversation_id,
        task_type=task.task_type,
        title=title,
        content_json=content_json,
        content_markdown=content_markdown,
        warnings_json=warnings_json,
        status=status,
    )
    session.add(output)
    session.commit()
    session.refresh(output)
    return output


def create_citation(
    session: Session,
    title: str,
    text: str,
    task_id: str | None = None,
    output_id: str | None = None,
    document_id: str | None = None,
    external_doc_id: str | None = None,
    chunk_id: str | None = None,
    score: float | None = None,
    source: str = "mock",
    metadata_json: str | None = None,
) -> Citation:
    _validate_citation_trace(
        title=title,
        text=text,
        source=source,
        document_id=document_id,
        external_doc_id=external_doc_id,
        chunk_id=chunk_id,
        metadata_json=metadata_json,
    )
    citation = Citation(
        task_id=task_id,
        output_id=output_id,
        document_id=document_id,
        external_doc_id=external_doc_id,
        chunk_id=chunk_id,
        title=title,
        text=text,
        score=score,
        source=source,
        metadata_json=metadata_json,
    )
    session.add(citation)
    session.commit()
    session.refresh(citation)
    return citation


def _validate_citation_trace(
    title: str,
    text: str,
    source: str,
    document_id: str | None,
    external_doc_id: str | None,
    chunk_id: str | None,
    metadata_json: str | None,
) -> None:
    if not title.strip():
        raise ValueError("Citation title is required.")
    if not text.strip():
        raise ValueError("Citation evidence text is required.")
    if source == "mock":
        return

    metadata = _metadata_from_json(metadata_json)
    binding = metadata.get("citation_binding")
    binding = binding if isinstance(binding, dict) else {}
    evidence_id = binding.get("evidence_id") or metadata.get("evidence_id")
    raw_source_type = (
        binding.get("source_type")
        or metadata.get("citation_source_type")
        or metadata.get("source_type")
    )
    source_type = _normalize_source_type(raw_source_type)
    if not evidence_id:
        raise ValueError("Real citation must include an evidence id.")
    if not source_type:
        raise ValueError("Real citation must include a source type.")
    if source_type == "document_chunk":
        if not chunk_id:
            raise ValueError("Document citation must include chunk_id.")
        if not document_id and not external_doc_id:
            raise ValueError("Document citation must include a document id.")
        return
    if source_type == "wiki_page":
        wiki_page_id = binding.get("wiki_page_id") or metadata.get("wiki_page_id")
        if not wiki_page_id:
            raise ValueError("Wiki citation must include wiki_page_id.")
        return
    raise ValueError("Real citation must include a known source type.")


def _metadata_from_json(metadata_json: str | None) -> dict[str, Any]:
    if not metadata_json:
        return {}
    try:
        value = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _normalize_source_type(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized


def create_output_with_citations(
    session: Session,
    task: GenerationTask,
    title: str,
    citations: list[dict],
    content_json: str | None = None,
    content_markdown: str | None = None,
    warnings_json: str | None = None,
    status: str = "completed",
) -> tuple[GeneratedOutput, list[Citation]]:
    for citation in citations:
        _validate_citation_trace(
            title=citation.get("title", ""),
            text=citation.get("text", ""),
            source=citation.get("source", "mock"),
            document_id=citation.get("document_id"),
            external_doc_id=citation.get("external_doc_id"),
            chunk_id=citation.get("chunk_id"),
            metadata_json=citation.get("metadata_json"),
        )
    output = create_output(
        session=session,
        task=task,
        title=title,
        content_json=content_json,
        content_markdown=content_markdown,
        warnings_json=warnings_json,
        status=status,
    )
    saved_citations = [
        create_citation(
            session=session,
            task_id=task.id,
            output_id=output.id,
            **citation,
        )
        for citation in citations
    ]
    return output, saved_citations


def get_task(session: Session, task_id: str) -> GenerationTask | None:
    return session.get(GenerationTask, task_id)


def get_output(session: Session, output_id: str) -> GeneratedOutput | None:
    return session.get(GeneratedOutput, output_id)


def list_output_citations(session: Session, output_id: str) -> list[Citation]:
    statement = select(Citation).where(Citation.output_id == output_id)
    return list(session.exec(statement).all())
