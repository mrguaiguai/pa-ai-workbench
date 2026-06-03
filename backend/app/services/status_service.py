from sqlmodel import Session
from sqlmodel import func
from sqlmodel import select

from app.models import Conversation
from app.models import Document
from app.models import DocumentChunk
from app.models import DocumentProcessingEvent
from app.models import GeneratedOutput
from app.models import GenerationTask


def _count(session: Session, model: type) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


def get_status_counts(session: Session) -> dict[str, int]:
    return {
        "documents": _count(session, Document),
        "document_chunks": _count(session, DocumentChunk),
        "document_events": _count(session, DocumentProcessingEvent),
        "conversations": _count(session, Conversation),
        "tasks": _count(session, GenerationTask),
        "outputs": _count(session, GeneratedOutput),
    }
