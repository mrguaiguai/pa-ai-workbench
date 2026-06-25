from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services.organization_service import create_native_faq_entry
from app.services.organization_service import create_native_skill
from app.services.organization_service import create_native_tag
from app.services.organization_service import delete_native_tag
from app.services.organization_service import delete_native_faq_entries
from app.services.organization_service import delete_native_skill
from app.services.organization_service import import_native_faq_entries
from app.services.organization_service import native_faq_entries
from app.services.organization_service import native_faq_entry
from app.services.organization_service import native_faq_import_progress
from app.services.organization_service import native_skill
from app.services.organization_service import native_tags
from app.services.organization_service import search_native_faq_entries
from app.services.organization_service import test_native_skill
from app.services.organization_service import native_workbench_organization_overview
from app.services.organization_service import toggle_native_favorite
from app.services.organization_service import update_native_faq_entry
from app.services.organization_service import update_native_skill
from app.services.organization_service import update_native_tag

router = APIRouter(prefix="/api/organization", tags=["organization"])


class NativeFaqEntryRequest(BaseModel):
    standard_question: str
    answers: list[str]
    similar_questions: list[str] = []
    negative_questions: list[str] = []
    answer_strategy: str = "all"
    tag_name: str = ""
    is_enabled: bool = True
    is_recommended: bool = False
    confirm_token: str | None = None


class NativeFaqDeleteRequest(BaseModel):
    entry_ids: list[int]
    confirm_token: str | None = None


class NativeFaqSearchRequest(BaseModel):
    query_text: str
    match_count: int = 5


class NativeFaqImportRequest(BaseModel):
    entries: list[NativeFaqEntryRequest]
    dry_run: bool = False
    confirm_token: str | None = None


class NativeTagMutationRequest(BaseModel):
    name: str | None = None
    color: str | None = None
    sort_order: int = 0
    confirm_token: str | None = None


class NativeFavoriteToggleRequest(BaseModel):
    resource_type: str
    resource_id: str
    favorited: bool
    confirm_token: str | None = None


class NativeSkillMutationRequest(BaseModel):
    name: str | None = None
    description: str
    instructions: str
    confirm_token: str | None = None


class NativeSkillActionRequest(BaseModel):
    confirm_token: str | None = None


@router.get("/native/overview")
def native_workbench_organization_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_workbench_organization_overview(limit=limit)


@router.get("/native/faq/{kb_id}/entries")
def native_faq_entries_api(
    kb_id: str,
    limit: int = Query(default=10, ge=1, le=10),
) -> dict[str, Any]:
    return native_faq_entries(kb_id=kb_id, limit=limit)


@router.get("/native/faq/{kb_id}/entries/{entry_id}")
def native_faq_entry_api(kb_id: str, entry_id: int) -> dict[str, Any]:
    return native_faq_entry(kb_id=kb_id, entry_id=entry_id)


@router.post("/native/faq/{kb_id}/entries")
def create_native_faq_entry_api(
    kb_id: str,
    payload: NativeFaqEntryRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return create_native_faq_entry(
            session=session,
            kb_id=kb_id,
            payload=payload.model_dump(exclude={"confirm_token"}),
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/native/faq/{kb_id}/entries/{entry_id}")
def update_native_faq_entry_api(
    kb_id: str,
    entry_id: int,
    payload: NativeFaqEntryRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return update_native_faq_entry(
            session=session,
            kb_id=kb_id,
            entry_id=entry_id,
            payload=payload.model_dump(exclude={"confirm_token"}),
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/native/faq/{kb_id}/entries")
def delete_native_faq_entries_api(
    kb_id: str,
    payload: NativeFaqDeleteRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return delete_native_faq_entries(
        session=session,
        kb_id=kb_id,
        entry_ids=payload.entry_ids,
        confirm_token=payload.confirm_token,
    )


@router.post("/native/faq/{kb_id}/search")
def search_native_faq_entries_api(kb_id: str, payload: NativeFaqSearchRequest) -> dict[str, Any]:
    return search_native_faq_entries(
        kb_id=kb_id,
        query_text=payload.query_text,
        match_count=payload.match_count,
    )


@router.post("/native/faq/{kb_id}/import")
def import_native_faq_entries_api(
    kb_id: str,
    payload: NativeFaqImportRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return import_native_faq_entries(
            session=session,
            kb_id=kb_id,
            entries=[
                entry.model_dump(exclude={"confirm_token"})
                for entry in payload.entries
            ],
            dry_run=payload.dry_run,
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/native/faq/import/progress/{task_id}")
def native_faq_import_progress_api(task_id: str) -> dict[str, Any]:
    return native_faq_import_progress(task_id=task_id)


@router.get("/native/tags/{kb_id}")
def native_tags_api(
    kb_id: str,
    limit: int = Query(default=10, ge=1, le=10),
) -> dict[str, Any]:
    return native_tags(kb_id=kb_id, limit=limit)


@router.post("/native/tags/{kb_id}")
def create_native_tag_api(
    kb_id: str,
    payload: NativeTagMutationRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return create_native_tag(
        session=session,
        kb_id=kb_id,
        payload=payload.model_dump(exclude={"confirm_token"}),
        confirm_token=payload.confirm_token,
    )


@router.put("/native/tags/{kb_id}/{tag_id}")
def update_native_tag_api(
    kb_id: str,
    tag_id: str,
    payload: NativeTagMutationRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return update_native_tag(
        session=session,
        kb_id=kb_id,
        tag_id=tag_id,
        payload=payload.model_dump(exclude={"confirm_token"}, exclude_none=True),
        confirm_token=payload.confirm_token,
    )


@router.delete("/native/tags/{kb_id}/{tag_id}")
def delete_native_tag_api(
    kb_id: str,
    tag_id: str,
    payload: NativeTagMutationRequest,
    force: bool = Query(default=False),
    content_only: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return delete_native_tag(
        session=session,
        kb_id=kb_id,
        tag_id=tag_id,
        force=force,
        content_only=content_only,
        confirm_token=payload.confirm_token,
    )


@router.post("/native/favorites/toggle")
def toggle_native_favorite_api(
    payload: NativeFavoriteToggleRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return toggle_native_favorite(
        session=session,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        favorited=payload.favorited,
        confirm_token=payload.confirm_token,
    )


@router.get("/native/skills/{name}")
def native_skill_api(name: str) -> dict[str, Any]:
    return native_skill(name=name)


@router.post("/native/skills")
def create_native_skill_api(
    payload: NativeSkillMutationRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return create_native_skill(
        session=session,
        payload=payload.model_dump(exclude={"confirm_token"}, exclude_none=True),
        confirm_token=payload.confirm_token,
    )


@router.put("/native/skills/{name}")
def update_native_skill_api(
    name: str,
    payload: NativeSkillMutationRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return update_native_skill(
        session=session,
        name=name,
        payload=payload.model_dump(exclude={"confirm_token"}, exclude_none=True),
        confirm_token=payload.confirm_token,
    )


@router.delete("/native/skills/{name}")
def delete_native_skill_api(
    name: str,
    payload: NativeSkillActionRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return delete_native_skill(
        session=session,
        name=name,
        confirm_token=payload.confirm_token,
    )


@router.post("/native/skills/{name}/test")
def test_native_skill_api(
    name: str,
    payload: NativeSkillActionRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return test_native_skill(
        session=session,
        name=name,
        confirm_token=payload.confirm_token,
    )
