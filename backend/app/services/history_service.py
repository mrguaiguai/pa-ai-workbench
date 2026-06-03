from sqlmodel import Session
from sqlmodel import select

from app.models import GeneratedOutput
from app.services.generation_service import get_output
from app.services.generation_service import list_output_citations


def list_history(session: Session) -> list[GeneratedOutput]:
    statement = select(GeneratedOutput).order_by(GeneratedOutput.created_at.desc())
    return list(session.exec(statement).all())


__all__ = ["get_output", "list_history", "list_output_citations"]

