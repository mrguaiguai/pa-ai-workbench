from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas import ConversationCreate
from app.schemas import ConversationCreateResponse
from app.schemas import ConversationListResponse
from app.schemas import ConversationMessageRead
from app.schemas import ConversationMessagesResponse
from app.schemas import ConversationRead
from app.services.conversation_service import create_conversation
from app.services.conversation_service import get_conversation
from app.services.conversation_service import list_conversations
from app.services.conversation_service import list_messages

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationCreateResponse)
def create_conversation_record(
    payload: ConversationCreate,
    session: Annotated[Session, Depends(get_session)],
) -> ConversationCreateResponse:
    conversation, messages = create_conversation(
        session=session,
        title=payload.title,
        summary=payload.summary,
        default_task_type=payload.default_task_type,
        created_by=payload.created_by,
        initial_message=payload.initial_message,
    )
    return ConversationCreateResponse(
        conversation=ConversationRead.model_validate(conversation),
        messages=[ConversationMessageRead.model_validate(message) for message in messages],
    )


@router.get("", response_model=ConversationListResponse)
def list_conversation_records(
    session: Annotated[Session, Depends(get_session)],
) -> ConversationListResponse:
    conversations = list_conversations(session)
    return ConversationListResponse(
        items=[ConversationRead.model_validate(conversation) for conversation in conversations],
        total=len(conversations),
    )


@router.get("/{conversation_id}", response_model=ConversationRead)
def read_conversation(
    conversation_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ConversationRead:
    conversation = get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationRead.model_validate(conversation)


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
def read_conversation_messages(
    conversation_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ConversationMessagesResponse:
    conversation = get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = list_messages(session, conversation_id)
    return ConversationMessagesResponse(
        items=[ConversationMessageRead.model_validate(message) for message in messages],
        total=len(messages),
    )

