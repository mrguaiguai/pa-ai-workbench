from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from sqlmodel import Session

from app.database import get_session
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
from app.services.document_service import reindex_document_chunks
from app.services.document_service import retry_index_document

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
) -> DocumentUploadResponse:
    document = await create_document(
        session=session,
        upload=file,
        title=title,
        business_area=business_area,
        document_type=document_type,
        source=source,
        keywords_json=keywords_json,
    )
    return DocumentUploadResponse(document=DocumentRead.model_validate(document))


@router.get("", response_model=DocumentListResponse)
def list_document_records(
    session: Annotated[Session, Depends(get_session)],
) -> DocumentListResponse:
    documents = list_documents(session)
    return DocumentListResponse(
        items=[DocumentRead.model_validate(document) for document in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentRead:
    document = get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(document)


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
        document=DocumentRead.model_validate(updated),
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
        document=DocumentRead.model_validate(updated),
        chunk_count=chunk_count,
        message="Document parsed and chunked. Vector indexing is pending.",
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
        document=DocumentRead.model_validate(updated),
        chunk_count=chunk_count,
        message="Document chunks rebuilt. Vector indexing is pending.",
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
        document=DocumentRead.model_validate(updated),
        message="Document chunks rebuilt. Vector indexing is pending.",
    )


def _require_document(session: Session, document_id: str):
    document = get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
