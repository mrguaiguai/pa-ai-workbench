from datetime import datetime
import json
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


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
    failed_step: str | None = None
    chunk_count: int = 0
    indexed_chunk_count: int = 0
    pending_chunk_count: int = 0
    failed_chunk_count: int = 0
    embedding_status: str | None = None
    processing_state: str = "waiting"
    processing_message: str | None = None
    next_action: str | None = None
    retryable: bool = False
    processing_seconds: int = 0
    processing_timed_out: bool = False
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


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    external_doc_id: str | None = None
    chunk_index: int
    title: str | None = None
    content: str
    content_hash: str
    token_count: int
    char_count: int
    start_char: int | None = None
    end_char: int | None = None
    page_number: int | None = None
    section_path: str | None = None
    paragraph_start_index: int | None = None
    paragraph_end_index: int | None = None
    business_area: str | None = None
    document_type: str | None = None
    source: str
    metadata_json: str | None = None
    embedding_status: str
    vector_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkRead]
    total: int


class DocumentProcessingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    external_doc_id: str | None = None
    step: str
    status: str
    message: str | None = None
    metadata_json: str | None = None
    error_message: str | None = None
    created_at: datetime


class DocumentProcessingEventListResponse(BaseModel):
    items: list[DocumentProcessingEventRead]
    total: int


class DocumentParseResponse(BaseModel):
    document: DocumentRead
    parse_metadata: dict


class DocumentIndexResponse(BaseModel):
    document: DocumentRead
    chunk_count: int
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
    evidence_id: str | None = None
    source_type: str | None = None
    wiki_page_id: str | None = None
    metadata_json: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def hydrate_evidence_fields(self) -> "CitationRead":
        metadata = _metadata_from_json(self.metadata_json)
        binding = metadata.get("citation_binding")
        binding = binding if isinstance(binding, dict) else {}
        if self.evidence_id is None:
            self.evidence_id = _optional_str(
                binding.get("evidence_id") or metadata.get("evidence_id")
            )
        if self.source_type is None:
            self.source_type = _normalize_source_type(
                binding.get("source_type")
                or metadata.get("citation_source_type")
                or metadata.get("source_type")
                or ("document_chunk" if self.chunk_id else None)
            )
        if self.wiki_page_id is None:
            self.wiki_page_id = _optional_str(
                binding.get("wiki_page_id") or metadata.get("wiki_page_id")
            )
        return self


def _metadata_from_json(metadata_json: str | None) -> dict[str, Any]:
    if not metadata_json:
        return {}
    try:
        value = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _normalize_source_type(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


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


class WeKnoraStatus(BaseModel):
    mode: str
    status: str
    connected: bool
    configured: bool
    base_url_configured: bool
    service_token_configured: bool
    workspace_configured: bool
    kb_configured: bool
    health_status: str | None = None
    message: str | None = None


class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    knowledge_backend: str
    mock_mode: bool
    weknora: WeKnoraStatus
    memory_recent_limit: int
    database: str
    counts: dict[str, int]


class ModelProviderStatus(BaseModel):
    provider: str
    model: str
    configured: bool
    mock: bool
    base_url_configured: bool
    api_key_configured: bool
    timeout_seconds: int
    temperature: float | None = None
    dimension: int | None = None


class ModelStatusResponse(BaseModel):
    chat_provider: str
    embedding_provider: str
    mock_mode: bool
    configured: bool
    chat: ModelProviderStatus
    embedding: ModelProviderStatus


class HistoryListResponse(BaseModel):
    items: list[GeneratedOutputRead]
    total: int


class EvidenceRead(BaseModel):
    evidence_id: str | None = None
    source_type: str | None = None
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    wiki_page_id: str | None = None
    title: str
    text: str
    score: float | None = None
    source: str
    metadata: dict


class RagRetrieveRequest(BaseModel):
    query: str
    filters: dict = Field(default_factory=dict)
    top_k: int = 8


class RagRetrieveResponse(BaseModel):
    items: list[EvidenceRead]
    total: int
    query: str
    filters: dict
    top_k: int


class WikiPageSummaryRead(BaseModel):
    id: str | None = None
    slug: str
    title: str
    page_type: str | None = None
    summary: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str
    metadata: dict


class WikiSearchResponse(BaseModel):
    items: list[WikiPageSummaryRead]
    total: int


class WikiCitationPayload(BaseModel):
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    output_id: str | None = None
    citation_id: str | None = None
    evidence_id: str | None = None
    source_type: str = "document_chunk"
    excerpt: str
    score: float | None = None
    metadata: dict = Field(default_factory=dict)


class WikiCitationRead(WikiCitationPayload):
    id: str
    wiki_page_id: str
    created_at: datetime


class WikiPageCreateRequest(BaseModel):
    slug: str
    title: str
    summary: str | None = None
    content_markdown: str = ""
    tags: list[str] = Field(default_factory=list)
    business_area: str | None = None
    page_type: str | None = None
    source_output_id: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)
    created_by: str | None = None
    metadata: dict = Field(default_factory=dict)
    citations: list[WikiCitationPayload] = Field(default_factory=list)


class WikiDraftFromOutputRequest(BaseModel):
    slug: str | None = None
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    business_area: str | None = None
    page_type: str | None = None
    created_by: str | None = None
    metadata: dict | None = None


class WikiPageUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    content_markdown: str | None = None
    tags: list[str] | None = None
    business_area: str | None = None
    page_type: str | None = None
    source_output_id: str | None = None
    source_document_ids: list[str] | None = None
    source_citation_ids: list[str] | None = None
    created_by: str | None = None
    metadata: dict | None = None
    citations: list[WikiCitationPayload] | None = None


class WikiPageRead(BaseModel):
    id: str | None = None
    slug: str
    title: str
    page_type: str | None = None
    summary: str | None = None
    content: str
    content_markdown: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    business_area: str | None = None
    source_output_id: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    source_citation_ids: list[str] = Field(default_factory=list)
    citations: list[EvidenceRead]
    wiki_citations: list[WikiCitationRead] = Field(default_factory=list)
    source: str
    metadata: dict
    created_by: str | None = None
    published_at: datetime | None = None
    embedding_status: str | None = None
    vector_id: str | None = None
    indexed_at: datetime | None = None
    wiki_state: str = "draft"
    wiki_message: str | None = None
    wiki_next_action: str | None = None
    wiki_retryable: bool = False
    wiki_retrievable: bool = False
    wiki_index_timed_out: bool = False
    wiki_processing_seconds: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
