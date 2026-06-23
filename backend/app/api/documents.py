from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from sqlmodel import Session

from app.database import get_session
from app.schemas import DocumentBulkRefreshResponse
from app.schemas import DocumentListResponse
from app.schemas import DocumentChunkListResponse
from app.schemas import DocumentChunkRead
from app.schemas import DocumentIndexResponse
from app.schemas import DocumentParseResponse
from app.schemas import DocumentProcessingEventListResponse
from app.schemas import DocumentProcessingEventRead
from app.schemas import DocumentRead
from app.schemas import DocumentRetryIndexResponse
from app.schemas import DocumentUploadResponse
from app.services.document_service import create_document
from app.services.document_service import DocumentWorkflowError
from app.services.document_service import get_document
from app.services.document_service import index_document_chunks
from app.services.document_service import list_document_chunks
from app.services.document_service import list_document_events
from app.services.document_service import list_documents
from app.services.document_service import parse_document_file
from app.services.document_service import recover_document_processing
from app.services.document_service import reindex_document_chunks
from app.services.document_service import refresh_document_statuses
from app.services.document_service import retry_index_document
from app.services.document_service import document_processing_summary

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    title: Annotated[str | None, Form()] = None,
    business_area: Annotated[str | None, Form()] = None,
    document_type: Annotated[str | None, Form()] = None,
    source: Annotated[str | None, Form()] = None,
    keywords_json: Annotated[str | None, Form()] = None,
    knowledge_base_id: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    document = await create_document(
        session=session,
        upload=file,
        title=title,
        business_area=business_area,
        document_type=document_type,
        source=source,
        keywords_json=keywords_json,
        knowledge_base_id=knowledge_base_id,
    )
    return DocumentUploadResponse(document=_document_read(session, document))


@router.get("", response_model=DocumentListResponse)
def list_document_records(
    session: Annotated[Session, Depends(get_session)],
    status: Annotated[str | None, Query()] = None,
    processing_state: Annotated[str | None, Query()] = None,
    has_error: Annotated[bool | None, Query()] = None,
    knowledge_backend: Annotated[str | None, Query()] = None,
    refresh_status: Annotated[bool, Query()] = False,
) -> DocumentListResponse:
    documents = list_documents(
        session=session,
        status=status,
        processing_state=processing_state,
        has_error=has_error,
        knowledge_backend=knowledge_backend,
        refresh_status=refresh_status,
    )
    return DocumentListResponse(
        items=[_document_read(session, document) for document in documents],
        total=len(documents),
    )


@router.post("/refresh-status", response_model=DocumentBulkRefreshResponse)
def refresh_document_records(
    session: Annotated[Session, Depends(get_session)],
    status: Annotated[str | None, Query()] = None,
    processing_state: Annotated[str | None, Query()] = None,
    has_error: Annotated[bool | None, Query()] = None,
    knowledge_backend: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> DocumentBulkRefreshResponse:
    documents = refresh_document_statuses(
        session=session,
        status=status,
        processing_state=processing_state,
        has_error=has_error,
        knowledge_backend=knowledge_backend,
        limit=limit,
    )
    return DocumentBulkRefreshResponse(
        items=[_document_read(session, document) for document in documents],
        total=len(documents),
        refreshed=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentRead:
    document = get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_read(session, document)


@router.post("/{document_id}/parse", response_model=DocumentParseResponse)
def parse_document(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentParseResponse:
    document = _require_document(session, document_id)
    try:
        updated, parse_metadata = parse_document_file(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentParseResponse(
        document=_document_read(session, updated),
        parse_metadata=parse_metadata,
    )


@router.post("/{document_id}/index", response_model=DocumentIndexResponse)
def index_document(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentIndexResponse:
    document = _require_document(session, document_id)
    try:
        updated, chunk_count = index_document_chunks(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentIndexResponse(
        document=_document_read(session, updated),
        chunk_count=chunk_count,
        message=_document_index_message(updated, default="Document parsed, chunked, embedded, and indexed."),
    )


@router.post("/{document_id}/reindex", response_model=DocumentIndexResponse)
def reindex_document(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentIndexResponse:
    document = _require_document(session, document_id)
    try:
        updated, chunk_count = reindex_document_chunks(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentIndexResponse(
        document=_document_read(session, updated),
        chunk_count=chunk_count,
        message=_document_index_message(
            updated,
            default="Document chunks rebuilt, embedded, and indexed.",
            retry=True,
        ),
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunkListResponse)
def read_document_chunks(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkListResponse:
    _require_document(session, document_id)
    chunks = list_document_chunks(session, document_id)
    return DocumentChunkListResponse(
        items=[DocumentChunkRead.model_validate(chunk) for chunk in chunks],
        total=len(chunks),
    )


@router.get("/{document_id}/events", response_model=DocumentProcessingEventListResponse)
def read_document_events(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentProcessingEventListResponse:
    _require_document(session, document_id)
    events = list_document_events(session, document_id)
    return DocumentProcessingEventListResponse(
        items=[DocumentProcessingEventRead.model_validate(event) for event in events],
        total=len(events),
    )


@router.post("/{document_id}/retry-index", response_model=DocumentRetryIndexResponse)
def retry_document_index(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentRetryIndexResponse:
    document = _require_document(session, document_id)
    try:
        updated = retry_index_document(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentRetryIndexResponse(
        document=_document_read(session, updated),
        message=_document_index_message(
            updated,
            default="Document chunks rebuilt, embedded, and indexed.",
            retry=True,
        ),
    )


@router.post("/{document_id}/retry-processing", response_model=DocumentRetryIndexResponse)
def retry_document_processing(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentRetryIndexResponse:
    document = _require_document(session, document_id)
    try:
        updated, message = recover_document_processing(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentRetryIndexResponse(
        document=_document_read(session, updated),
        message=message,
    )


def _require_document(session: Session, document_id: str):
    document = get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _document_index_message(document, default: str, retry: bool = False) -> str:
    if document.knowledge_backend != "weknora_api":
        return default
    if retry:
        return "WeKnora native document retry/status refresh completed; PA did not run local chunking or vector indexing."
    return "WeKnora native document status refreshed; PA did not run local chunking or vector indexing."


def _document_read(session: Session, document) -> DocumentRead:
    chunks = list_document_chunks(session, document.id)
    indexed_count = sum(1 for chunk in chunks if chunk.embedding_status == "indexed")
    failed_count = sum(1 for chunk in chunks if chunk.embedding_status == "failed")
    pending_count = len(chunks) - indexed_count - failed_count
    processing_summary = document_processing_summary(document)
    return DocumentRead.model_validate(document).model_copy(
        update={
            "chunk_count": len(chunks),
            "indexed_chunk_count": indexed_count,
            "pending_chunk_count": pending_count,
            "failed_chunk_count": failed_count,
            "embedding_status": _embedding_status(
                chunk_count=len(chunks),
                indexed_count=indexed_count,
                failed_count=failed_count,
            ),
            **processing_summary,
        }
    )


def _embedding_status(
    chunk_count: int,
    indexed_count: int,
    failed_count: int,
) -> str:
    if chunk_count == 0:
        return "none"
    if failed_count:
        return "failed"
    if indexed_count == chunk_count:
        return "indexed"
    if indexed_count:
        return "partial"
    return "pending"
