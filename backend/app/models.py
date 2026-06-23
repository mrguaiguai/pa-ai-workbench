from datetime import datetime
from uuid import uuid4

from sqlmodel import Field
from sqlmodel import SQLModel


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now() -> datetime:
    return datetime.utcnow()


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class Document(TimestampMixin, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: new_id("doc"), primary_key=True)
    title: str = Field(index=True)
    business_area: str | None = Field(default=None, index=True)
    document_type: str | None = Field(default=None, index=True)
    source: str | None = Field(default=None)
    keywords_json: str | None = Field(default=None)
    file_name: str | None = Field(default=None)
    file_path: str | None = Field(default=None)
    file_size: int | None = Field(default=None)
    mime_type: str | None = Field(default=None)
    knowledge_backend: str = Field(default="mock", index=True)
    external_doc_id: str | None = Field(default=None, index=True)
    summary: str | None = Field(default=None)
    status: str = Field(default="uploaded", index=True)
    error_message: str | None = Field(default=None)
    failed_step: str | None = Field(default=None, index=True)


class DocumentChunk(TimestampMixin, table=True):
    __tablename__ = "document_chunks"

    id: str = Field(default_factory=lambda: new_id("chunk"), primary_key=True)
    document_id: str = Field(index=True)
    external_doc_id: str | None = Field(default=None, index=True)
    chunk_index: int = Field(index=True)
    title: str | None = Field(default=None, index=True)
    content: str
    content_hash: str = Field(index=True)
    token_count: int = Field(default=0)
    char_count: int = Field(default=0)
    start_char: int | None = Field(default=None)
    end_char: int | None = Field(default=None)
    page_number: int | None = Field(default=None, index=True)
    section_path: str | None = Field(default=None)
    paragraph_start_index: int | None = Field(default=None)
    paragraph_end_index: int | None = Field(default=None)
    business_area: str | None = Field(default=None, index=True)
    document_type: str | None = Field(default=None, index=True)
    source: str = Field(default="document", index=True)
    metadata_json: str | None = Field(default=None)
    embedding_status: str = Field(default="pending", index=True)
    vector_id: str | None = Field(default=None, index=True)


class DocumentProcessingEvent(SQLModel, table=True):
    __tablename__ = "document_processing_events"

    id: str = Field(default_factory=lambda: new_id("evt"), primary_key=True)
    document_id: str = Field(index=True)
    external_doc_id: str | None = Field(default=None, index=True)
    step: str = Field(index=True)
    status: str = Field(index=True)
    message: str | None = Field(default=None)
    metadata_json: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class Conversation(TimestampMixin, table=True):
    __tablename__ = "conversations"

    id: str = Field(default_factory=lambda: new_id("conv"), primary_key=True)
    title: str = Field(index=True)
    summary: str | None = Field(default=None)
    default_task_type: str = Field(default="knowledge_qa", index=True)
    created_by: str | None = Field(default=None)


class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_messages"

    id: str = Field(default_factory=lambda: new_id("msg"), primary_key=True)
    conversation_id: str = Field(index=True)
    role: str = Field(index=True)
    content: str
    metadata_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class GenerationTask(TimestampMixin, table=True):
    __tablename__ = "generation_tasks"

    id: str = Field(default_factory=lambda: new_id("task"), primary_key=True)
    conversation_id: str | None = Field(default=None, index=True)
    task_type: str = Field(index=True)
    title: str | None = Field(default=None)
    input_json: str | None = Field(default=None)
    status: str = Field(default="created", index=True)
    current_step: str | None = Field(default=None)
    progress: int = Field(default=0)
    error_message: str | None = Field(default=None)


class GeneratedOutput(TimestampMixin, table=True):
    __tablename__ = "generated_outputs"

    id: str = Field(default_factory=lambda: new_id("out"), primary_key=True)
    task_id: str = Field(index=True)
    conversation_id: str | None = Field(default=None, index=True)
    task_type: str = Field(index=True)
    title: str
    content_json: str | None = Field(default=None)
    content_markdown: str | None = Field(default=None)
    warnings_json: str | None = Field(default=None)
    status: str = Field(default="completed", index=True)


class Citation(SQLModel, table=True):
    __tablename__ = "citations"

    id: str = Field(default_factory=lambda: new_id("cite"), primary_key=True)
    task_id: str | None = Field(default=None, index=True)
    output_id: str | None = Field(default=None, index=True)
    document_id: str | None = Field(default=None, index=True)
    external_doc_id: str | None = Field(default=None, index=True)
    chunk_id: str | None = Field(default=None, index=True)
    title: str
    text: str
    score: float | None = Field(default=None)
    source: str = Field(default="mock", index=True)
    metadata_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class KnowledgeBaseSelectionSnapshot(TimestampMixin, table=True):
    __tablename__ = "knowledge_base_selection_snapshots"

    id: str = Field(default_factory=lambda: new_id("kbsel"), primary_key=True)
    workspace_id: str | None = Field(default=None, index=True)
    kb_id: str = Field(index=True)
    selection_source: str = Field(default="pa_active_selection", index=True)
    mapping_name: str | None = Field(default=None, index=True)
    name: str | None = Field(default=None)
    type: str | None = Field(default=None, index=True)
    source: str = Field(default="weknora_api", index=True)
    status: str = Field(default="active", index=True)
    metadata_json: str | None = Field(default=None)


class WikiPage(TimestampMixin, table=True):
    __tablename__ = "wiki_pages"

    id: str = Field(default_factory=lambda: new_id("wiki"), primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str = Field(index=True)
    summary: str | None = Field(default=None)
    content_markdown: str = Field(default="")
    status: str = Field(default="draft", index=True)
    tags_json: str | None = Field(default=None)
    business_area: str | None = Field(default=None, index=True)
    page_type: str | None = Field(default=None, index=True)
    source_output_id: str | None = Field(default=None, index=True)
    source_document_ids_json: str | None = Field(default=None)
    source_citation_ids_json: str | None = Field(default=None)
    created_by: str | None = Field(default=None, index=True)
    published_at: datetime | None = Field(default=None, index=True)
    embedding_status: str = Field(default="pending", index=True)
    vector_id: str | None = Field(default=None, index=True)
    indexed_at: datetime | None = Field(default=None, index=True)
    metadata_json: str | None = Field(default=None)


class WikiCitation(SQLModel, table=True):
    __tablename__ = "wiki_citations"

    id: str = Field(default_factory=lambda: new_id("wikicite"), primary_key=True)
    wiki_page_id: str = Field(index=True)
    document_id: str | None = Field(default=None, index=True)
    external_doc_id: str | None = Field(default=None, index=True)
    chunk_id: str | None = Field(default=None, index=True)
    output_id: str | None = Field(default=None, index=True)
    citation_id: str | None = Field(default=None, index=True)
    evidence_id: str | None = Field(default=None, index=True)
    source_type: str = Field(default="document_chunk", index=True)
    excerpt: str
    score: float | None = Field(default=None)
    metadata_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class WikiPageCache(TimestampMixin, table=True):
    __tablename__ = "wiki_pages_cache"

    id: str = Field(default_factory=lambda: new_id("wiki"), primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str = Field(index=True)
    page_type: str | None = Field(default=None, index=True)
    summary: str | None = Field(default=None)
    content: str | None = Field(default=None)
    source: str = Field(default="mock", index=True)
    metadata_json: str | None = Field(default=None)
