from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlmodel import Session

from app.database import get_session
from app.schemas import NativeMutationAuditListResponse
from app.schemas import NativeMutationAuditRead
from app.services.native_audit_service import list_native_mutation_audits
from app.services.native_audit_service import native_audit_wnid_summary

router = APIRouter(prefix="/api/native-audit", tags=["native-audit"])


@router.get("/events", response_model=NativeMutationAuditListResponse)
def list_native_audit_events(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    capability: Annotated[str | None, Query(max_length=80)] = None,
    operation: Annotated[str | None, Query(max_length=120)] = None,
    target_type: Annotated[str | None, Query(max_length=80)] = None,
    target_id: Annotated[str | None, Query(max_length=160)] = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
    wnid_capability: Annotated[str | None, Query(max_length=80)] = None,
) -> NativeMutationAuditListResponse:
    events = list_native_mutation_audits(
        session=session,
        limit=limit,
        capability=capability,
        operation=operation,
        target_type=target_type,
        target_id=target_id,
        status=status,
        wnid_capability=wnid_capability,
    )
    return NativeMutationAuditListResponse(
        items=[_audit_read(event) for event in events],
        total=len(events),
    )


def _audit_read(event) -> NativeMutationAuditRead:
    return NativeMutationAuditRead.model_validate(event).model_copy(
        update=native_audit_wnid_summary(event)
    )
