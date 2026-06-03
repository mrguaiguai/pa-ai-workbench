from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


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


class ConversationCreate(BaseModel):
    title: str | None = None
    summary: str | None = None
    default_task_type: str = "knowledge_qa"
    created_by: str | None = None
    initial_message: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str | None = None
    default_task_type: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationRead]
    total: int


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    metadata_json: str | None = None
    created_at: datetime


class ConversationCreateResponse(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]


class ConversationMessagesResponse(BaseModel):
    items: list[ConversationMessageRead]
    total: int


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str | None = None
    task_type: str
    title: str | None = None
    input_json: str | None = None
    status: str
    current_step: str | None = None
    progress: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class GeneratedOutputRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    conversation_id: str | None = None
    task_type: str
    title: str
    content_json: str | None = None
    content_markdown: str | None = None
    warnings_json: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str | None = None
    output_id: str | None = None
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    title: str
    text: str
    score: float | None = None
    source: str
    metadata_json: str | None = None
    created_at: datetime


class OutputDetailResponse(BaseModel):
    output: GeneratedOutputRead
    citations: list[CitationRead]


class AnalysisRunRequest(BaseModel):
    conversation_id: str | None = None
    task_type: str = "knowledge_qa"
    title: str | None = None
    query_or_topic: str
    business_area: str | None = None
    document_type: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    extra_requirements: str | None = None


class AnalysisRunResponse(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]
    task: TaskRead
    output: GeneratedOutputRead
    citations: list[CitationRead]


class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    knowledge_backend: str
    mock_mode: bool
    memory_recent_limit: int
    database: str
    counts: dict[str, int]


class HistoryListResponse(BaseModel):
    items: list[GeneratedOutputRead]
    total: int


class EvidenceRead(BaseModel):
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    title: str
    text: str
    score: float | None = None
    source: str
    metadata: dict


class WikiPageSummaryRead(BaseModel):
    slug: str
    title: str
    page_type: str
    summary: str
    source: str
    metadata: dict


class WikiSearchResponse(BaseModel):
    items: list[WikiPageSummaryRead]
    total: int


class WikiPageRead(BaseModel):
    slug: str
    title: str
    page_type: str
    summary: str
    content: str
    citations: list[EvidenceRead]
    source: str
    metadata: dict
