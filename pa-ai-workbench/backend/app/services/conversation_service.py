from datetime import datetime

from sqlmodel import Session
from sqlmodel import select

from app.models import Conversation
from app.models import ConversationMessage

VALID_MESSAGE_ROLES = {"user", "assistant", "system_status"}


def create_conversation(
    session: Session,
    title: str | None = None,
    summary: str | None = None,
    default_task_type: str = "knowledge_qa",
    created_by: str | None = None,
    initial_message: str | None = None,
) -> tuple[Conversation, list[ConversationMessage]]:
    conversation = Conversation(
        title=title or "新会话",
        summary=summary,
        default_task_type=default_task_type,
        created_by=created_by,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    messages: list[ConversationMessage] = []
    if initial_message:
        messages.append(
            add_message(
                session=session,
                conversation=conversation,
                role="user",
                content=initial_message,
            )
        )
    return conversation, messages


def list_conversations(session: Session) -> list[Conversation]:
    statement = select(Conversation).order_by(Conversation.updated_at.desc())
    return list(session.exec(statement).all())


def get_conversation(session: Session, conversation_id: str) -> Conversation | None:
    return session.get(Conversation, conversation_id)


def list_messages(session: Session, conversation_id: str) -> list[ConversationMessage]:
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    return list(session.exec(statement).all())


def add_message(
    session: Session,
    conversation: Conversation,
    role: str,
    content: str,
    metadata_json: str | None = None,
) -> ConversationMessage:
    if role not in VALID_MESSAGE_ROLES:
        raise ValueError(f"Unsupported conversation message role: {role}")

    message = ConversationMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        metadata_json=metadata_json,
    )
    conversation.updated_at = datetime.utcnow()
    session.add(message)
    session.add(conversation)
    session.commit()
    session.refresh(message)
    session.refresh(conversation)
    return message

