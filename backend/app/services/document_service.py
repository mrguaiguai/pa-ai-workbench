import json
import os
from typing import Any

from fastapi import UploadFile
from sqlmodel import Session
from sqlmodel import select

from app import pathing as _pathing  # noqa: F401
from app.config import get_settings
from app.models import Document
from app.models import DocumentChunk
from app.models import DocumentProcessingEvent
from app.models import utc_now
from app.storage.file_store import save_upload_file
from knowledge_engine.chunking import Chunker
from knowledge_engine.chunking import DocumentChunkCandidate
from knowledge_engine.chunking import ParagraphChunker
from knowledge_engine.embeddings.base import EmbeddingProvider
from knowledge_engine.embeddings.factory import get_embedding_provider
from knowledge_engine.embeddings.schemas import EmbeddingVector
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.parsers import DocumentParser
from knowledge_engine.parsers import FileDocumentParser
from knowledge_engine.parsers import ParsedDocument
from knowledge_engine.vectorstores import VectorRecord
from knowledge_engine.vectorstores import VectorStore
from knowledge_engine.vectorstores import get_vector_store

MAX_ERROR_MESSAGE_CHARS = 500
DOCUMENT_PROCESSING_TIMEOUT_SECONDS = 30 * 60
PROCESSING_STATUSES = {"uploaded", "parsing", "chunking", "embedding", "indexing"}


class DocumentWorkflowError(Exception):
    """Raised when a document processing workflow step fails."""


async def create_document(
    session: Session,
    upload: UploadFile,
    title: str | None = None,
    business_area: str | None = None,
    document_type: str | None = None,
    source: str | None = None,
    keywords_json: str | None = None,
) -> Document:
    stored_file = await save_upload_file(upload)
    settings = get_settings()
    document = Document(
        title=title or stored_file.file_name,
        business_area=business_area,
        document_type=document_type,
        source=source or "manual",
        keywords_json=keywords_json,
        file_name=stored_file.file_name,
        file_path=stored_file.file_path,
        file_size=stored_file.file_size,
        mime_type=stored_file.mime_type,
        knowledge_backend=settings.knowledge_backend,
        external_doc_id=None,
        status="uploaded",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    if settings.knowledge_backend == "weknora_api":
        _upload_document_to_weknora(session, document)
    return document


def list_documents(session: Session) -> list[Document]:
    statement = select(Document).order_by(Document.created_at.desc())
    documents = list(session.exec(statement).all())
    for document in documents:
        sync_document_status(session, document)
    return documents


def get_document(session: Session, document_id: str) -> Document | None:
    document = session.get(Document, document_id)
    if document is not None:
        sync_document_status(session, document)
    return document


def sync_document_status(session: Session, document: Document) -> Document:
    if document.knowledge_backend != "weknora_api" or not document.external_doc_id:
        return document
    try:
        status = _weknora_backend().get_document_status(document.external_doc_id)
    except KnowledgeBackendUnavailableError as exc:
        _record_event(
            session=session,
            document=document,
            step="weknora_status",
            status="failed",
            message="WeKnora document status refresh failed.",
            error_message=str(exc)[:MAX_ERROR_MESSAGE_CHARS],
        )
        session.commit()
        return document

    new_status = str(status.get("status") or "unknown")
    if (
        document.status == new_status
        and document.error_message == status.get("error_message")
        and document.failed_step == status.get("failed_step")
    ):
        return document

    document.status = new_status
    document.error_message = status.get("error_message")
    document.failed_step = status.get("failed_step")
    document.updated_at = utc_now()
    session.add(document)
    _record_event(
        session=session,
        document=document,
        step="weknora_status",
        status="completed",
        message=status.get("message") or "WeKnora document status refreshed.",
        metadata=status.get("metadata") or {},
        error_message=status.get("error_message"),
    )
    session.commit()
    session.refresh(document)
    return document


def parse_document_file(
    session: Session,
    document: Document,
    parser: DocumentParser | None = None,
) -> tuple[Document, dict]:
    _transition_document(
        session=session,
        document=document,
        status="parsing",
        step="parse",
        event_status="started",
        message="Document parsing started.",
    )
    try:
        parsed = _parse_document(document, parser)
        metadata = _parse_metadata(parsed)
        _transition_document(
            session=session,
            document=document,
            status="parsed",
            step="parse",
            event_status="completed",
            message="Document parsing completed.",
            metadata=metadata,
        )
        return document, metadata
    except Exception as exc:
        _fail_document_step(session, document, failed_step="parse", exc=exc)
        raise DocumentWorkflowError(str(exc)) from exc


def index_document_chunks(
    session: Session,
    document: Document,
    parser: DocumentParser | None = None,
    chunker: Chunker | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
) -> tuple[Document, int]:
    try:
        resolved_embedding_provider = embedding_provider or get_embedding_provider()
        resolved_vector_store = vector_store or get_vector_store()
        _transition_document(
            session=session,
            document=document,
            status="parsing",
            step="index",
            event_status="started",
            message="Document parse/chunk workflow started.",
        )
        parsed = _parse_document(document, parser)
        _transition_document(
            session=session,
            document=document,
            status="parsed",
            step="parse",
            event_status="completed",
            message="Document parsing completed.",
            metadata=_parse_metadata(parsed),
        )

        _transition_document(
            session=session,
            document=document,
            status="chunking",
            step="chunk",
            event_status="started",
            message="Document chunking started.",
        )
        resolved_chunker = chunker or ParagraphChunker()
        chunks = resolved_chunker.chunk(parsed)
        existing_vector_ids = _document_vector_ids(session, document.id)
        indexed_chunks = _replace_document_chunks(session, document, chunks)
        _transition_document(
            session=session,
            document=document,
            status="chunked",
            step="chunk",
            event_status="completed",
            message="Document chunking completed.",
            metadata={"chunk_count": len(chunks)},
        )

        _transition_document(
            session=session,
            document=document,
            status="indexing",
            step="index",
            event_status="started",
            message="Document vector indexing started.",
            metadata={"chunk_count": len(indexed_chunks)},
        )
        _index_chunks_with_embeddings(
            session=session,
            document=document,
            chunks=indexed_chunks,
            embedding_provider=resolved_embedding_provider,
            vector_store=resolved_vector_store,
            old_vector_ids=existing_vector_ids,
        )
        _transition_document(
            session=session,
            document=document,
            status="indexed",
            step="index",
            event_status="completed",
            message="Document vector indexing completed.",
            metadata={
                "chunk_count": len(indexed_chunks),
                "vector_count": len(indexed_chunks),
            },
        )
        return document, len(indexed_chunks)
    except Exception as exc:
        _fail_document_step(session, document, failed_step="index", exc=exc)
        raise DocumentWorkflowError(str(exc)) from exc


def reindex_document_chunks(
    session: Session,
    document: Document,
    parser: DocumentParser | None = None,
    chunker: Chunker | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
) -> tuple[Document, int]:
    _record_event(
        session=session,
        document=document,
        step="reindex",
        status="started",
        message="Document reindex requested.",
    )
    session.commit()
    return index_document_chunks(
        session=session,
        document=document,
        parser=parser,
        chunker=chunker,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def retry_index_document(session: Session, document: Document) -> Document:
    updated, _ = reindex_document_chunks(session, document)
    return updated


def recover_document_processing(session: Session, document: Document) -> tuple[Document, str]:
    if document.knowledge_backend != "weknora_api":
        updated, _ = reindex_document_chunks(session, document)
        return updated, "Document chunks rebuilt, embedded, and indexed."

    document = sync_document_status(session, document)
    summary = document_processing_summary(document)
    if document.status == "indexed":
        return document, "Document is already indexed."
    if summary["processing_state"] == "processing" and not summary["processing_timed_out"]:
        _record_event(
            session=session,
            document=document,
            step="weknora_retry",
            status="skipped",
            message="WeKnora retry skipped because processing is still active.",
            metadata={
                "status": document.status,
                "processing_seconds": summary["processing_seconds"],
            },
        )
        session.commit()
        return document, "Document is still processing; no duplicate retry submitted."
    if not document.file_path:
        raise DocumentWorkflowError("Document has no stored file path for retry.")

    prior_external_doc_id = document.external_doc_id
    _record_event(
        session=session,
        document=document,
        step="weknora_retry",
        status="started",
        message="WeKnora document processing retry started.",
        metadata={
            "prior_external_doc_id": prior_external_doc_id,
            "prior_status": document.status,
            "prior_failed_step": document.failed_step,
            "processing_timed_out": summary["processing_timed_out"],
        },
    )
    session.commit()
    _upload_document_to_weknora(
        session=session,
        document=document,
        operation="retry",
        prior_external_doc_id=prior_external_doc_id,
    )
    if document.status == "failed" and document.failed_step == "weknora_retry":
        raise DocumentWorkflowError(document.error_message or "WeKnora retry upload failed.")
    return document, "Document retry submitted to WeKnora using the existing PA record."


def document_processing_summary(document: Document) -> dict[str, Any]:
    processing_seconds = _processing_seconds(document)
    timed_out = (
        document.status in PROCESSING_STATUSES
        and processing_seconds >= _processing_timeout_seconds()
    )
    if document.status == "indexed":
        return {
            "processing_state": "ready",
            "processing_message": "Document is indexed and ready for grounded answers.",
            "next_action": "ask",
            "retryable": False,
            "processing_seconds": processing_seconds,
            "processing_timed_out": False,
        }
    if document.status == "failed":
        return {
            "processing_state": "failed",
            "processing_message": _failed_processing_message(document),
            "next_action": "retry",
            "retryable": True,
            "processing_seconds": processing_seconds,
            "processing_timed_out": False,
        }
    if timed_out:
        return {
            "processing_state": "stalled",
            "processing_message": _stalled_processing_message(document),
            "next_action": "retry",
            "retryable": True,
            "processing_seconds": processing_seconds,
            "processing_timed_out": True,
        }
    if document.status in PROCESSING_STATUSES:
        return {
            "processing_state": "processing",
            "processing_message": _active_processing_message(document),
            "next_action": "wait",
            "retryable": False,
            "processing_seconds": processing_seconds,
            "processing_timed_out": False,
        }
    return {
        "processing_state": "waiting",
        "processing_message": "Document is waiting for processing.",
        "next_action": "refresh",
        "retryable": False,
        "processing_seconds": processing_seconds,
        "processing_timed_out": False,
    }


def list_document_chunks(session: Session, document_id: str) -> list[DocumentChunk]:
    document = session.get(Document, document_id)
    if document and document.knowledge_backend == "weknora_api" and document.external_doc_id:
        try:
            return _list_weknora_document_chunks(document)
        except KnowledgeBackendUnavailableError as exc:
            _record_event(
                session=session,
                document=document,
                step="weknora_chunks",
                status="failed",
                message="WeKnora document chunk preview failed.",
                error_message=str(exc)[:MAX_ERROR_MESSAGE_CHARS],
            )
            session.commit()
    return _list_local_document_chunks(session, document_id)


def _list_local_document_chunks(session: Session, document_id: str) -> list[DocumentChunk]:
    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(session.exec(statement).all())


def _list_weknora_document_chunks(document: Document) -> list[DocumentChunk]:
    raw_chunks = _weknora_backend().list_document_chunks(document.external_doc_id or "")
    now = utc_now()
    chunks: list[DocumentChunk] = []
    for index, raw in enumerate(raw_chunks):
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        chunks.append(
            DocumentChunk(
                id=str(raw.get("id") or f"weknora_chunk_{document.id}_{index}"),
                document_id=document.id,
                external_doc_id=str(raw.get("external_doc_id") or document.external_doc_id or ""),
                chunk_index=int(raw.get("chunk_index") or index),
                title=raw.get("title") or document.title,
                content=str(raw.get("content") or ""),
                content_hash=str(raw.get("content_hash") or ""),
                token_count=int(raw.get("token_count") or 0),
                char_count=int(raw.get("char_count") or len(str(raw.get("content") or ""))),
                start_char=raw.get("start_char"),
                end_char=raw.get("end_char"),
                page_number=raw.get("page_number"),
                section_path=_to_json(raw.get("section_path")) if raw.get("section_path") else None,
                paragraph_start_index=raw.get("paragraph_start_index"),
                paragraph_end_index=raw.get("paragraph_end_index"),
                business_area=document.business_area,
                document_type=document.document_type,
                source=str(raw.get("source") or "weknora_api"),
                metadata_json=_to_json(metadata),
                embedding_status=str(raw.get("embedding_status") or "indexed"),
                vector_id=raw.get("vector_id"),
                created_at=now,
                updated_at=now,
            )
        )
    return sorted(chunks, key=lambda chunk: chunk.chunk_index)


def list_document_events(session: Session, document_id: str) -> list[DocumentProcessingEvent]:
    statement = (
        select(DocumentProcessingEvent)
        .where(DocumentProcessingEvent.document_id == document_id)
        .order_by(DocumentProcessingEvent.created_at)
    )
    return list(session.exec(statement).all())


def _parse_document(
    document: Document,
    parser: DocumentParser | None = None,
) -> ParsedDocument:
    if not document.file_path:
        raise DocumentWorkflowError("Document has no stored file path.")
    resolved_parser = parser or FileDocumentParser()
    return resolved_parser.parse(
        document.file_path,
        metadata={
            "document_id": document.id,
            "title": document.title,
            "business_area": document.business_area,
            "document_type": document.document_type,
            "source": document.source,
            "mime_type": document.mime_type,
        },
    )


def _upload_document_to_weknora(
    session: Session,
    document: Document,
    operation: str = "upload",
    prior_external_doc_id: str | None = None,
) -> None:
    step = "weknora_upload" if operation == "upload" else "weknora_retry"
    _record_event(
        session=session,
        document=document,
        step=step,
        status="started",
        message=(
            "WeKnora document upload started."
            if operation == "upload"
            else "WeKnora document retry upload started."
        ),
        metadata={"prior_external_doc_id": prior_external_doc_id}
        if prior_external_doc_id
        else None,
    )
    session.commit()
    try:
        uploaded = _weknora_backend().upload_document(
            document.file_path or "",
            metadata={
                "document_id": document.id,
                "title": document.title,
                "business_area": document.business_area,
                "document_type": document.document_type,
                "source": document.source,
                "keywords_json": document.keywords_json,
                "file_name": document.file_name,
                "mime_type": document.mime_type,
            },
        )
    except KnowledgeBackendUnavailableError as exc:
        _fail_document_step(
            session=session,
            document=document,
            failed_step=step,
            exc=DocumentWorkflowError(str(exc)),
        )
        return

    document.external_doc_id = uploaded.external_doc_id
    document.knowledge_backend = uploaded.source
    document.status = uploaded.status
    document.error_message = None
    document.failed_step = None
    document.updated_at = utc_now()
    session.add(document)
    _record_event(
        session=session,
        document=document,
        step=step,
        status="completed",
        message=(
            "WeKnora document upload completed."
            if operation == "upload"
            else "WeKnora document retry upload completed."
        ),
        metadata={
            "external_doc_id": uploaded.external_doc_id,
            "prior_external_doc_id": prior_external_doc_id,
            "status": uploaded.status,
            "title": uploaded.title,
            "source": uploaded.source,
            "weknora": uploaded.metadata,
        },
    )
    session.commit()
    session.refresh(document)


def _weknora_backend() -> WeKnoraApiBackend:
    settings = get_settings()
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
    )


def _processing_seconds(document: Document) -> int:
    delta = utc_now() - document.updated_at
    return max(int(delta.total_seconds()), 0)


def _processing_timeout_seconds() -> int:
    value = os.getenv("DOCUMENT_PROCESSING_TIMEOUT_SECONDS")
    if value is None:
        return DOCUMENT_PROCESSING_TIMEOUT_SECONDS
    try:
        return max(int(value), 1)
    except ValueError:
        return DOCUMENT_PROCESSING_TIMEOUT_SECONDS


def _active_processing_message(document: Document) -> str:
    if document.status == "uploaded":
        return "Document is uploaded and waiting for WeKnora processing."
    if document.status == "parsing":
        return "WeKnora is parsing the document."
    if document.status == "chunking":
        return "WeKnora is splitting the document into chunks."
    if document.status in {"embedding", "indexing"}:
        return "WeKnora is embedding and indexing the document."
    return "Document processing is active."


def _failed_processing_message(document: Document) -> str:
    step = document.failed_step or "processing"
    if step in {"parse", "parsing"}:
        return "Document parsing failed; retry after checking the file format."
    if step in {"chunk", "chunking"}:
        return "Document chunking failed; retry will resubmit the existing document record."
    if step in {"embedding", "embed"}:
        return "Document embedding failed; retry will resubmit to WeKnora."
    if step in {"index", "indexing"}:
        return "Document vector indexing failed; retry will resubmit to WeKnora."
    if step in {"weknora_upload", "weknora_retry"}:
        return "WeKnora upload failed; retry will use the stored PA document file."
    return "Document processing failed; retry is available."


def _stalled_processing_message(document: Document) -> str:
    return (
        f"Document has stayed in {document.status} longer than "
        f"{_processing_timeout_seconds()} seconds; retry is available."
    )


def _parse_metadata(parsed: ParsedDocument) -> dict:
    return {
        "file_name": parsed.file_name,
        "file_type": parsed.file_type,
        "mime_type": parsed.mime_type,
        "title": parsed.title,
        "char_count": parsed.char_count,
        "section_count": parsed.section_count,
    }


def _replace_document_chunks(
    session: Session,
    document: Document,
    chunks: list[DocumentChunkCandidate],
) -> list[DocumentChunk]:
    for existing in _list_local_document_chunks(session, document.id):
        session.delete(existing)
    session.flush()
    models: list[DocumentChunk] = []
    for candidate in chunks:
        model = _chunk_candidate_to_model(document, candidate)
        session.add(model)
        models.append(model)
    session.flush()
    return models


def _document_vector_ids(session: Session, document_id: str) -> list[str]:
    return [
        chunk.vector_id
        for chunk in _list_local_document_chunks(session, document_id)
        if chunk.vector_id
    ]


def _chunk_candidate_to_model(
    document: Document,
    candidate: DocumentChunkCandidate,
) -> DocumentChunk:
    return DocumentChunk(
        document_id=document.id,
        external_doc_id=document.external_doc_id,
        chunk_index=candidate.chunk_index,
        title=candidate.title,
        content=candidate.content,
        content_hash=candidate.content_hash,
        token_count=candidate.token_count,
        char_count=candidate.char_count,
        start_char=candidate.start_char,
        end_char=candidate.end_char,
        page_number=candidate.page_number,
        section_path=_to_json(candidate.section_path),
        paragraph_start_index=candidate.paragraph_start_index,
        paragraph_end_index=candidate.paragraph_end_index,
        business_area=document.business_area,
        document_type=document.document_type,
        source="document",
        metadata_json=_to_json(candidate.metadata),
        embedding_status="pending",
        vector_id=None,
    )


def _index_chunks_with_embeddings(
    session: Session,
    document: Document,
    chunks: list[DocumentChunk],
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    old_vector_ids: list[str] | None = None,
) -> None:
    if not chunks:
        _delete_old_vectors_after_reindex(
            session=session,
            document=document,
            vector_store=vector_store,
            old_vector_ids=old_vector_ids or [],
            current_vector_ids=[],
        )
        session.commit()
        return

    embeddings = embedding_provider.embed_batch([chunk.content for chunk in chunks])
    if len(embeddings) != len(chunks):
        raise DocumentWorkflowError(
            "EmbeddingProvider returned a vector count that did not match chunks."
        )

    records = [
        _chunk_to_vector_record(document, chunk, embedding)
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    vector_store.upsert(records)
    _delete_old_vectors_after_reindex(
        session=session,
        document=document,
        vector_store=vector_store,
        old_vector_ids=old_vector_ids or [],
        current_vector_ids=[record.id for record in records],
    )

    updated_at = utc_now()
    for chunk, record in zip(chunks, records, strict=True):
        chunk.embedding_status = "indexed"
        chunk.vector_id = record.id
        chunk.updated_at = updated_at
        session.add(chunk)
    session.commit()


def _delete_old_vectors_after_reindex(
    session: Session,
    document: Document,
    vector_store: VectorStore,
    old_vector_ids: list[str],
    current_vector_ids: list[str],
) -> None:
    current_ids = set(current_vector_ids)
    old_ids_to_delete = [
        vector_id for vector_id in old_vector_ids if vector_id not in current_ids
    ]
    if not old_ids_to_delete:
        return

    deleted_count = vector_store.delete(old_ids_to_delete)
    _record_event(
        session=session,
        document=document,
        step="index",
        status="deleted",
        message="Existing document vectors deleted after successful reindex.",
        metadata={
            "requested_vector_count": len(old_ids_to_delete),
            "deleted_vector_count": deleted_count,
        },
    )


def _chunk_to_vector_record(
    document: Document,
    chunk: DocumentChunk,
    embedding: EmbeddingVector,
) -> VectorRecord:
    return VectorRecord(
        id=_chunk_vector_id(chunk),
        vector=embedding.vector,
        text=chunk.content,
        metadata=_chunk_vector_metadata(document, chunk, embedding),
    )


def _chunk_vector_id(chunk: DocumentChunk) -> str:
    return f"document_chunk:{chunk.id}"


def _chunk_vector_metadata(
    document: Document,
    chunk: DocumentChunk,
    embedding: EmbeddingVector,
) -> dict[str, Any]:
    return {
        "source_type": "document",
        "source": chunk.source,
        "document_id": document.id,
        "external_doc_id": document.external_doc_id,
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "title": chunk.title or document.title,
        "document_title": document.title,
        "business_area": chunk.business_area,
        "document_type": chunk.document_type,
        "content_hash": chunk.content_hash,
        "token_count": chunk.token_count,
        "char_count": chunk.char_count,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
        "page_number": chunk.page_number,
        "section_path": _from_json(chunk.section_path) or [],
        "paragraph_start_index": chunk.paragraph_start_index,
        "paragraph_end_index": chunk.paragraph_end_index,
        "embedding_provider": embedding.provider,
        "embedding_model": embedding.model,
        "embedding_dimension": embedding.dimension,
        "embedding_text_hash": embedding.text_hash,
        "chunk_metadata": _from_json(chunk.metadata_json) or {},
    }


def _transition_document(
    session: Session,
    document: Document,
    status: str,
    step: str,
    event_status: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    document.status = status
    document.error_message = None
    document.failed_step = None
    document.updated_at = utc_now()
    session.add(document)
    _record_event(
        session=session,
        document=document,
        step=step,
        status=event_status,
        message=message,
        metadata=metadata,
    )
    session.commit()
    session.refresh(document)


def _fail_document_step(
    session: Session,
    document: Document,
    failed_step: str,
    exc: Exception,
) -> None:
    session.rollback()
    error_message = str(exc)[:MAX_ERROR_MESSAGE_CHARS]
    document.status = "failed"
    document.failed_step = failed_step
    document.error_message = error_message
    document.updated_at = utc_now()
    session.add(document)
    _record_event(
        session=session,
        document=document,
        step=failed_step,
        status="failed",
        message=f"Document {failed_step} failed.",
        error_message=error_message,
    )
    session.commit()
    session.refresh(document)


def _record_event(
    session: Session,
    document: Document,
    step: str,
    status: str,
    message: str | None = None,
    metadata: dict | None = None,
    error_message: str | None = None,
) -> None:
    session.add(
        DocumentProcessingEvent(
            document_id=document.id,
            external_doc_id=document.external_doc_id,
            step=step,
            status=status,
            message=message,
            metadata_json=_to_json(metadata) if metadata else None,
            error_message=error_message,
        )
    )


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _from_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
