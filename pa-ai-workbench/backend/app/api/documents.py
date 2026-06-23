from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi import UploadFile
from sqlmodel import Session

from app.database import get_session
from app.schemas import DocumentBulkRefreshResponse
from app.schemas import DocumentChunkActionResponse
from app.schemas import DocumentChunkEnabledRequest
from app.schemas import DocumentLifecycleActionResponse
from app.schemas import DocumentListResponse
from app.schemas import DocumentChunkListResponse
from app.schemas import DocumentChunkMutationRequest
from app.schemas import DocumentChunkRead
from app.schemas import DocumentIndexResponse
from app.schemas import DocumentManualCreateRequest
from app.schemas import DocumentParseResponse
from app.schemas import DocumentProcessingEventListResponse
from app.schemas import DocumentProcessingEventRead
from app.schemas import DocumentRead
from app.schemas import DocumentRetryIndexResponse
from app.schemas import DocumentSpansResponse
from app.schemas import DocumentUploadResponse
from app.schemas import DocumentUrlCreateRequest
from app.services.document_service import cancel_native_document_parse
from app.services.document_service import create_document
from app.services.document_service import create_document_from_url
from app.services.document_service import create_manual_document
from app.services.document_service import delete_native_document_chunk
from app.services.document_service import delete_native_generated_question
from app.services.document_service import delete_native_document
from app.services.document_service import DocumentWorkflowError
from app.services.document_service import get_document
from app.services.document_service import get_document_spans
from app.services.document_service import index_document_chunks
from app.services.document_service import list_document_chunks
from app.services.document_service import list_document_events
from app.services.document_service import list_documents
from app.services.document_service import parse_document_file
from app.services.document_service import read_native_document_file
from app.services.document_service import read_document_chunk
from app.services.document_service import recover_document_processing
from app.services.document_service import reparse_native_document
from app.services.document_service import reindex_document_chunks
from app.services.document_service import refresh_document_statuses
from app.services.document_service import retry_index_document
from app.services.document_service import set_native_document_chunk_enabled
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


@router.post("/url", response_model=DocumentUploadResponse)
def ingest_document_url(
    payload: DocumentUrlCreateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentUploadResponse:
    try:
        document = create_document_from_url(
            session=session,
            url=payload.url,
            title=payload.title,
            business_area=payload.business_area,
            document_type=payload.document_type,
            source=payload.source,
            keywords_json=payload.keywords_json,
            knowledge_base_id=payload.knowledge_base_id,
        )
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentUploadResponse(document=_document_read(session, document))


@router.post("/manual", response_model=DocumentUploadResponse)
def ingest_manual_document(
    payload: DocumentManualCreateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentUploadResponse:
    try:
        document = create_manual_document(
            session=session,
            title=payload.title,
            content=payload.content,
            business_area=payload.business_area,
            document_type=payload.document_type,
            source=payload.source,
            keywords_json=payload.keywords_json,
            knowledge_base_id=payload.knowledge_base_id,
        )
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@router.get("/{document_id}/chunks/{chunk_id}", response_model=DocumentChunkRead)
def read_document_chunk_detail(
    document_id: str,
    chunk_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkRead:
    document = _require_document(session, document_id)
    try:
        chunk = read_document_chunk(session, document, chunk_id)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentChunkRead.model_validate(chunk)


@router.patch("/{document_id}/chunks/{chunk_id}/enabled", response_model=DocumentChunkActionResponse)
def set_document_chunk_enabled(
    document_id: str,
    chunk_id: str,
    payload: DocumentChunkEnabledRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkActionResponse:
    document = _require_document(session, document_id)
    try:
        chunk = set_native_document_chunk_enabled(
            session=session,
            document=document,
            chunk_id=chunk_id,
            is_enabled=payload.is_enabled,
            confirm=payload.confirm,
            reason=payload.reason,
        )
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _chunk_action_response(
        session=session,
        document=document,
        chunk=chunk,
        action="toggle",
        audit_step="weknora_chunk_toggle",
        message="WeKnora chunk toggle completed.",
    )


@router.delete("/{document_id}/chunks/{chunk_id}", response_model=DocumentChunkActionResponse)
def delete_document_chunk_record(
    document_id: str,
    chunk_id: str,
    payload: DocumentChunkMutationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkActionResponse:
    document = _require_document(session, document_id)
    try:
        message = delete_native_document_chunk(
            session=session,
            document=document,
            chunk_id=chunk_id,
            confirm=payload.confirm,
            reason=payload.reason,
        )
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _chunk_action_response(
        session=session,
        document=document,
        chunk=None,
        action="delete_chunk",
        audit_step="weknora_chunk_delete",
        message=message,
    )


@router.delete(
    "/{document_id}/chunks/{chunk_id}/questions/{question_id}",
    response_model=DocumentChunkActionResponse,
)
def delete_document_chunk_generated_question(
    document_id: str,
    chunk_id: str,
    question_id: str,
    payload: DocumentChunkMutationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkActionResponse:
    document = _require_document(session, document_id)
    try:
        chunk = delete_native_generated_question(
            session=session,
            document=document,
            chunk_id=chunk_id,
            question_id=question_id,
            confirm=payload.confirm,
            reason=payload.reason,
        )
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _chunk_action_response(
        session=session,
        document=document,
        chunk=chunk,
        action="delete_generated_question",
        audit_step="weknora_chunk_question_delete",
        message="WeKnora generated question delete completed.",
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


@router.get("/{document_id}/spans", response_model=DocumentSpansResponse)
def read_document_spans(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentSpansResponse:
    document = _require_document(session, document_id)
    try:
        spans = get_document_spans(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentSpansResponse(**spans)


@router.get("/{document_id}/preview")
def preview_document_file(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    document = _require_document(session, document_id)
    try:
        file_payload = read_native_document_file(session, document, preview=True)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = _file_response_headers(file_payload, inline=True)
    return Response(
        content=file_payload["content"],
        media_type=file_payload["content_type"],
        headers=headers,
    )


@router.get("/{document_id}/download")
def download_document_file(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    document = _require_document(session, document_id)
    try:
        file_payload = read_native_document_file(session, document, preview=False)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = _file_response_headers(file_payload, inline=False)
    return Response(
        content=file_payload["content"],
        media_type=file_payload["content_type"],
        headers=headers,
    )


@router.post("/{document_id}/native-reparse", response_model=DocumentLifecycleActionResponse)
def reparse_document_native(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentLifecycleActionResponse:
    document = _require_document(session, document_id)
    try:
        updated, message = reparse_native_document(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _lifecycle_action_response(session, updated, "reparse", message)


@router.post("/{document_id}/cancel-processing", response_model=DocumentLifecycleActionResponse)
def cancel_document_processing(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentLifecycleActionResponse:
    document = _require_document(session, document_id)
    try:
        updated, message = cancel_native_document_parse(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _lifecycle_action_response(session, updated, "cancel", message)


@router.delete("/{document_id}", response_model=DocumentLifecycleActionResponse)
def delete_document_record(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentLifecycleActionResponse:
    document = _require_document(session, document_id)
    try:
        updated, message = delete_native_document(session, document)
    except DocumentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _lifecycle_action_response(session, updated, "delete", message)


def _require_document(session: Session, document_id: str):
    document = get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _lifecycle_action_response(
    session: Session,
    document,
    action: str,
    message: str,
) -> DocumentLifecycleActionResponse:
    return DocumentLifecycleActionResponse(
        document=_document_read(session, document),
        action=action,
        message=message,
    )


def _chunk_action_response(
    session: Session,
    document,
    chunk,
    action: str,
    message: str,
    audit_step: str,
) -> DocumentChunkActionResponse:
    return DocumentChunkActionResponse(
        document=_document_read(session, document),
        chunk=DocumentChunkRead.model_validate(chunk) if chunk is not None else None,
        action=action,
        message=message,
        audit_step=audit_step,
    )


def _file_response_headers(file_payload: dict, inline: bool) -> dict[str, str]:
    headers: dict[str, str] = {"Cache-Control": "private, max-age=120"}
    disposition = file_payload.get("content_disposition")
    if isinstance(disposition, str) and disposition:
        headers["Content-Disposition"] = disposition
    else:
        mode = "inline" if inline else "attachment"
        headers["Content-Disposition"] = f"{mode}; filename=document"
    return headers


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
