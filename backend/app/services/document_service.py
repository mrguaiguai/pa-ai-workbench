import json

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
from knowledge_engine.parsers import DocumentParser
from knowledge_engine.parsers import FileDocumentParser
from knowledge_engine.parsers import ParsedDocument

MAX_ERROR_MESSAGE_CHARS = 500


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
    return document


def list_documents(session: Session) -> list[Document]:
    statement = select(Document).order_by(Document.created_at.desc())
    return list(session.exec(statement).all())


def get_document(session: Session, document_id: str) -> Document | None:
    return session.get(Document, document_id)


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
) -> tuple[Document, int]:
    try:
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
        _replace_document_chunks(session, document, chunks)
        _transition_document(
            session=session,
            document=document,
            status="chunked",
            step="chunk",
            event_status="completed",
            message="Document chunking completed; vector indexing is pending.",
            metadata={"chunk_count": len(chunks)},
        )
        _record_event(
            session=session,
            document=document,
            step="index",
            status="deferred",
            message="Vector indexing is deferred until vector store and embedding pipeline tasks.",
            metadata={"chunk_count": len(chunks)},
        )
        session.commit()
        session.refresh(document)
        return document, len(chunks)
    except Exception as exc:
        _fail_document_step(session, document, failed_step="index", exc=exc)
        raise DocumentWorkflowError(str(exc)) from exc


def reindex_document_chunks(
    session: Session,
    document: Document,
    parser: DocumentParser | None = None,
    chunker: Chunker | None = None,
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
    )


def retry_index_document(session: Session, document: Document) -> Document:
    updated, _ = reindex_document_chunks(session, document)
    return updated


def list_document_chunks(session: Session, document_id: str) -> list[DocumentChunk]:
    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(session.exec(statement).all())


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
) -> None:
    for existing in list_document_chunks(session, document.id):
        session.delete(existing)
    session.flush()
    for candidate in chunks:
        session.add(_chunk_candidate_to_model(document, candidate))


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
