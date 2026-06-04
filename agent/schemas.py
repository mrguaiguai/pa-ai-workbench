from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from typing import Any


class AgentTaskType(StrEnum):
    KNOWLEDGE_QA = "knowledge_qa"
    POLICY_ANALYSIS = "policy_analysis"
    CASE_REVIEW = "case_review"


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentEventType(StrEnum):
    STARTED = "started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    CITATION_ADDED = "citation_added"
    WARNING = "warning"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class AgentRequest:
    task_id: str
    conversation_id: str
    task_type: str
    query_or_topic: str
    title: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    document_ids: list[str] = field(default_factory=list)
    extra_requirements: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Citation:
    title: str
    text: str
    source: str
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_id: str | None = None
    source_type: str | None = None
    wiki_page_id: str | None = None


@dataclass(frozen=True)
class AgentEvent:
    task_id: str
    event_type: str
    message: str
    conversation_id: str | None = None
    step: str | None = None
    progress: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    conversation_id: str
    task_type: str
    status: str
    title: str
    content: dict[str, Any]
    markdown: str
    citations: list[Citation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    memory_updates: list[dict[str, Any]] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
