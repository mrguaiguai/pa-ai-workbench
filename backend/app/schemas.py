from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    business_area: str | None = None
    document_type: str | None = None
    source: str | None = None
    keywords_json: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    knowledge_backend: str
    external_doc_id: str | None = None
    summary: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int


class DocumentUploadResponse(BaseModel):
    document: DocumentRead


class DocumentRetryIndexResponse(BaseModel):
    document: DocumentRead
    message: str

