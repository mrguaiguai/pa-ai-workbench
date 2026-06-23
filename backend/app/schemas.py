from datetime import datetime
import json
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from knowledge_engine.retrieval import RETRIEVAL_OPTIONS_KEY
from knowledge_engine.retrieval import normalize_retrieval_options
from knowledge_engine.retrieval import retrieval_debug_trace
from knowledge_engine.source_scope import normalize_source_scope


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


class DocumentUrlCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    title: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    source: str | None = None
    keywords_json: str | None = None
    knowledge_base_id: str | None = None


class DocumentManualCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=200000)
    business_area: str | None = None
    document_type: str | None = None
    source: str | None = None
    keywords_json: str | None = None
    knowledge_base_id: str | None = None


class DocumentRetryIndexResponse(BaseModel):
    document: DocumentRead
    message: str


class DocumentLifecycleActionResponse(BaseModel):
    document: DocumentRead
    action: str
    message: str
    evidence_type: str = "live_api"
    source: str = "weknora_api"


class DocumentChunkMutationRequest(BaseModel):
    confirm: bool = False
    reason: str | None = Field(default=None, max_length=300)


class DocumentChunkEnabledRequest(DocumentChunkMutationRequest):
    is_enabled: bool


class DocumentSpansResponse(BaseModel):
    source: str
    external_doc_id: str | None = None
    parse_status: str | None = None
    current_attempt: int | None = None
    current_stage: str | None = None
    trace: dict = Field(default_factory=dict)
    last_error: dict | None = None


class DocumentBulkRefreshResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    refreshed: int


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


class DocumentChunkActionResponse(BaseModel):
    document: DocumentRead
    chunk: DocumentChunkRead | None = None
    action: str
    message: str
    evidence_type: str = "live_api"
    source: str = "weknora_api"
    audit_step: str


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
    citation_count: int = 0
    weknora_citation_count: int = 0
    mock_citation_count: int = 0
    document_citation_count: int = 0
    wiki_citation_count: int = 0
    traceable_citation_count: int = 0
    warning_count: int = 0
    evidence_state: str = "unknown"
    citation_blocked: bool = False
    citation_blocker: str | None = None
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
        binding_metadata = binding.get("metadata")
        binding_metadata = binding_metadata if isinstance(binding_metadata, dict) else {}
        if self.evidence_id is None:
            wiki_page_id = _wiki_page_id_from_metadata(binding, metadata, binding_metadata)
            self.evidence_id = _optional_str(
                binding.get("evidence_id") or metadata.get("evidence_id")
                or (f"wiki_page:{wiki_page_id}" if wiki_page_id else None)
            )
        if self.source_type is None:
            self.source_type = _normalize_source_type(
                binding.get("source_type")
                or metadata.get("citation_source_type")
                or metadata.get("source_type")
                or binding_metadata.get("source_type")
                or ("wiki_page" if _wiki_page_id_from_metadata(binding, metadata, binding_metadata) else None)
                or ("document_chunk" if self.chunk_id else None)
            )
        if self.wiki_page_id is None:
            self.wiki_page_id = _optional_str(
                _wiki_page_id_from_metadata(binding, metadata, binding_metadata)
            )
        return self


class CitationLocateRequest(BaseModel):
    id: str | None = None
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    evidence_id: str | None = None
    source_type: str | None = None
    wiki_page_id: str | None = None
    source: str | None = None
    metadata_json: str | None = None
    metadata: dict = Field(default_factory=dict)


class CitationLocateResponse(BaseModel):
    located: bool
    target_type: str | None = None
    route: str | None = None
    ui_hash: str | None = None
    message: str
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    chunk_index: int | None = None
    wiki_page_id: str | None = None
    wiki_slug: str | None = None


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


def _wiki_page_id_from_metadata(
    binding: dict[str, Any],
    metadata: dict[str, Any],
    binding_metadata: dict[str, Any],
) -> str | None:
    return _first_optional_str(
        binding.get("wiki_page_id"),
        metadata.get("wiki_page_id"),
        metadata.get("weknora_wiki_page_id"),
        metadata.get("pa_wiki_page_id"),
        metadata.get("id"),
        binding_metadata.get("wiki_page_id"),
        binding_metadata.get("weknora_wiki_page_id"),
        binding_metadata.get("pa_wiki_page_id"),
        binding_metadata.get("id"),
    )


def _first_optional_str(*values: object) -> str | None:
    for value in values:
        normalized = _optional_str(value)
        if normalized:
            return normalized
    return None


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
    retrieval_scope: str = "all"
    current_run: dict[str, Any] = Field(default_factory=dict)
    expected_source_types: list[str] = Field(default_factory=list)
    should_answer_insufficient: bool = False
    forbidden_anchors: list[str] = Field(default_factory=list)
    question_type: str | None = None

    @field_validator("retrieval_scope")
    @classmethod
    def validate_retrieval_scope(cls, value: str) -> str:
        try:
            return normalize_source_scope(value)
        except ValueError as exc:
            raise ValueError("retrieval_scope must be all, document, or wiki") from exc

    @field_validator("expected_source_types")
    @classmethod
    def validate_expected_source_types(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            source_type = _normalize_source_type(value)
            if source_type not in {"document_chunk", "wiki_page"}:
                raise ValueError(
                    "expected_source_types must contain document_chunk or wiki_page"
                )
            if source_type not in normalized:
                normalized.append(source_type)
        return normalized

    @field_validator("forbidden_anchors")
    @classmethod
    def validate_forbidden_anchors(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            anchor = str(value or "").strip()
            if anchor and anchor not in normalized:
                normalized.append(anchor)
        return normalized


class AnalysisRunResponse(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]
    task: TaskRead
    output: GeneratedOutputRead
    citations: list[CitationRead]


class NativeAgentItem(BaseModel):
    id: str | None = None
    name: str
    description: str | None = None
    avatar: str | None = None
    is_builtin: bool = False
    creator_name: str | None = None
    runnable_by_viewer: bool = True
    agent_mode: str
    agent_type: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    knowledge_base_count: int = 0
    model_configured: bool = False
    rerank_configured: bool = False
    web_search_enabled: bool = False
    suggested_prompt_count: int = 0


class NativeAgentPreset(BaseModel):
    agent_type: str | None = None
    name: str | None = None
    description: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)


class NativeAgentSuggestedQuestion(BaseModel):
    question: str | None = None
    source: str | None = None
    knowledge_base_id: str | None = None


class NativeAgentCatalogResponse(BaseModel):
    schema_version: str
    source: str
    status: str
    agents: list[NativeAgentItem]
    presets: list[NativeAgentPreset] = Field(default_factory=list)
    placeholder_groups: dict[str, int] = Field(default_factory=dict)
    suggested_questions: list[NativeAgentSuggestedQuestion] = Field(default_factory=list)
    selected_agent_id: str | None = None
    active_knowledge_base_id: str | None = None
    surfaces: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class NativeAgentQaRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    agent_id: str | None = Field(default=None, max_length=120)
    conversation_id: str | None = None
    title: str | None = Field(default=None, max_length=300)
    knowledge_base_ids: list[str] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    web_search_enabled: bool = False


class NativeAgentQaRuntime(BaseModel):
    native_session_id: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    event_counts: dict = Field(default_factory=dict)
    tool_names: list[str] = Field(default_factory=list)
    reference_count: int = 0
    saved_citation_count: int = 0
    citation_blocked: bool = False
    warnings: list[str] = Field(default_factory=list)
    assistant_message_id: str | None = None
    user_message_id: str | None = None
    evidence_type: str = "live_api"
    source: str = "weknora_api"


class NativeAgentQaResponse(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]
    task: TaskRead
    output: GeneratedOutputRead
    citations: list[CitationRead]
    runtime: NativeAgentQaRuntime


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
    kb_mapping: dict[str, Any] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    knowledge_backend: str
    mock_mode: bool
    weknora: WeKnoraStatus
    backend_capabilities: dict[str, Any] = Field(default_factory=dict)
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


RAG_FILTER_KEYS = {
    "business_area",
    "current_run",
    "document_ids",
    "document_type",
    "external_doc_id",
    "external_doc_ids",
    "kb_id",
    "kb_ids",
    "knowledge_base_id",
    "knowledge_base_ids",
    "knowledge_ids",
    RETRIEVAL_OPTIONS_KEY,
    "source_type",
    "source_scope",
}


def _validate_rag_filters(filters: dict) -> dict:
    unknown = sorted(str(key) for key in filters if str(key) not in RAG_FILTER_KEYS)
    if unknown:
        raise ValueError("Unsupported RAG filter(s): " + ", ".join(unknown))
    source_scope = filters.get("source_scope")
    source_type = filters.get("source_type")
    if source_scope not in (None, ""):
        normalized_scope = normalize_source_scope(source_scope)
        filters["source_scope"] = normalized_scope
        if normalized_scope == "document":
            filters["source_type"] = "document_chunk"
        elif normalized_scope == "wiki":
            filters["source_type"] = "wiki_page"
        else:
            filters.pop("source_type", None)
        if RETRIEVAL_OPTIONS_KEY in filters:
            filters[RETRIEVAL_OPTIONS_KEY] = normalize_retrieval_options(
                filters.get(RETRIEVAL_OPTIONS_KEY)
            )
        return filters
    if source_type in (None, ""):
        if RETRIEVAL_OPTIONS_KEY in filters:
            filters[RETRIEVAL_OPTIONS_KEY] = normalize_retrieval_options(
                filters.get(RETRIEVAL_OPTIONS_KEY)
            )
        return filters
    if str(source_type).strip().lower() == "all":
        filters.pop("source_type", None)
        filters["source_scope"] = "all"
        if RETRIEVAL_OPTIONS_KEY in filters:
            filters[RETRIEVAL_OPTIONS_KEY] = normalize_retrieval_options(
                filters.get(RETRIEVAL_OPTIONS_KEY)
            )
        return filters
    normalized = _normalize_source_type(source_type)
    if normalized not in {"document_chunk", "wiki_page"}:
        raise ValueError("source_type must be document_chunk or wiki_page")
    filters["source_type"] = normalized
    filters["source_scope"] = "document" if normalized == "document_chunk" else "wiki"
    if RETRIEVAL_OPTIONS_KEY in filters:
        filters[RETRIEVAL_OPTIONS_KEY] = normalize_retrieval_options(
            filters.get(RETRIEVAL_OPTIONS_KEY)
        )
    return filters


class RagRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    filters: dict = Field(default_factory=dict)
    top_k: int = Field(default=8, ge=1, le=50)

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, filters: dict) -> dict:
        return _validate_rag_filters(filters)


class RagRetrieveResponse(BaseModel):
    items: list[EvidenceRead]
    total: int
    query: str
    filters: dict
    top_k: int
    warnings: list[str] = Field(default_factory=list)


class RagDebugRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    filters: dict = Field(default_factory=dict)
    top_k: int = Field(default=8, ge=1, le=50)

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, filters: dict) -> dict:
        return _validate_rag_filters(filters)


class RagDebugEvidenceRead(BaseModel):
    rank: int
    source_type: str | None = None
    source: str
    score: float | None = None
    evidence_id: str | None = None
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    wiki_page_id: str | None = None
    title: str
    summary: str
    metadata: dict = Field(default_factory=dict)


class RagDebugError(BaseModel):
    error_code: str
    message: str
    operation: str | None = None
    retryable: bool = False


class RagDebugResponse(BaseModel):
    trace_id: str
    status: str
    query: str
    filters: dict
    top_k: int
    requested_source_type: str | None = None
    retrieval_options: dict = Field(default_factory=dict)
    debug_trace: list[dict] = Field(default_factory=list)
    items: list[RagDebugEvidenceRead]
    total: int
    warnings: list[str] = Field(default_factory=list)
    error: RagDebugError | None = None

    @model_validator(mode="after")
    def hydrate_debug_trace(self) -> "RagDebugResponse":
        if not self.retrieval_options:
            self.retrieval_options = normalize_retrieval_options(
                self.filters.get(RETRIEVAL_OPTIONS_KEY)
            )
        if not self.debug_trace:
            self.debug_trace = retrieval_debug_trace(self.retrieval_options)
        return self


class NativeKnowledgeChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    title: str | None = Field(default=None, max_length=300)
    knowledge_base_ids: list[str] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    web_search_enabled: bool = False
    current_run: dict = Field(default_factory=dict)


class NativeKnowledgeChatRuntime(BaseModel):
    native_session_id: str | None = None
    event_counts: dict = Field(default_factory=dict)
    reference_count: int = 0
    saved_citation_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    assistant_message_id: str | None = None
    user_message_id: str | None = None
    current_run_guard: dict = Field(default_factory=dict)
    evidence_type: str = "live_api"
    source: str = "weknora_api"


class NativeKnowledgeChatResponse(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]
    task: TaskRead
    output: GeneratedOutputRead
    citations: list[CitationRead]
    runtime: NativeKnowledgeChatRuntime


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


class NativeWikiPageSaveRequest(BaseModel):
    confirm_token: str
    slug: str | None = None
    title: str
    summary: str | None = None
    content_markdown: str = ""
    page_type: str | None = None
    status: str = "draft"
    aliases: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    chunk_refs: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class NativeWikiPageDeleteRequest(BaseModel):
    confirm_token: str
    slug: str


class NativeWikiConfirmRequest(BaseModel):
    confirm_token: str


class NativeWikiIssueStatusRequest(BaseModel):
    confirm_token: str
    status: str


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
