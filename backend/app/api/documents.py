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
from app.schemas import DocumentRead
from app.schemas import DocumentRetryIndexResponse
from app.schemas import DocumentUploadResponse
from app.services.document_service import create_document
from app.services.document_service import get_document
from app.services.document_service import list_documents
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


@router.post("/{document_id}/retry-index", response_model=DocumentRetryIndexResponse)
def retry_document_index(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentRetryIndexResponse:
    document = get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    updated = retry_index_document(session, document)
    return DocumentRetryIndexResponse(
        document=DocumentRead.model_validate(updated),
        message="Document queued for mock indexing.",
    )

