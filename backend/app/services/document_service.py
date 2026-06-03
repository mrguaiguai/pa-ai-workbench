from datetime import datetime

from fastapi import UploadFile
from sqlmodel import Session
from sqlmodel import select

from app.config import get_settings
from app.models import Document
from app.storage.file_store import save_upload_file


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


def retry_index_document(session: Session, document: Document) -> Document:
    document.status = "indexing"
    document.error_message = None
    document.updated_at = datetime.utcnow()
    session.add(document)
    session.commit()
    session.refresh(document)
    return document

