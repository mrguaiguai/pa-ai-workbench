from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Protocol

VALID_MEMORY_ROLES = {"user", "assistant", "system_status"}
SENSITIVE_METADATA_KEYS = {
    "api_key",
    "authorization",
    "password",
    "prompt",
    "secret",
    "system_prompt",
    "token",
}


@dataclass(frozen=True)
class ConversationMemory:
    conversation_id: str
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class MemoryStore(Protocol):
    def append(self, memory: ConversationMemory) -> ConversationMemory:
        raise NotImplementedError

    def list_messages(self, conversation_id: str) -> list[ConversationMemory]:
        raise NotImplementedError


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._messages: dict[str, list[ConversationMemory]] = defaultdict(list)

    def append(self, memory: ConversationMemory) -> ConversationMemory:
        self._messages[memory.conversation_id].append(memory)
        return memory

    def list_messages(self, conversation_id: str) -> list[ConversationMemory]:
        return list(self._messages.get(conversation_id, []))


class MemoryManager:
    def __init__(
        self,
        store: MemoryStore | None = None,
        recent_limit: int = 10,
        max_content_chars: int = 4000,
    ) -> None:
        self.store = store or InMemoryMemoryStore()
        self.recent_limit = recent_limit
        self.max_content_chars = max_content_chars

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMemory:
        if role not in VALID_MEMORY_ROLES:
            raise ValueError(f"Unsupported memory role: {role}")

        memory = ConversationMemory(
            conversation_id=conversation_id,
            role=role,
            content=self._sanitize_content(content),
            metadata=self._sanitize_metadata(metadata or {}),
        )
        return self.store.append(memory)

    def add_user_message(
        self,
        conversation_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMemory:
        return self.add_message(conversation_id, "user", content, metadata)

    def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMemory:
        return self.add_message(conversation_id, "assistant", content, metadata)

    def add_system_status(
        self,
        conversation_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMemory:
        return self.add_message(conversation_id, "system_status", content, metadata)

    def list_recent(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[ConversationMemory]:
        resolved_limit = limit if limit is not None else self.recent_limit
        messages = self.store.list_messages(conversation_id)
        return messages[-resolved_limit:] if resolved_limit > 0 else []

    def list_recent_dicts(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "role": memory.role,
                "content": memory.content,
                "metadata": memory.metadata,
                "created_at": memory.created_at.isoformat(),
            }
            for memory in self.list_recent(conversation_id, limit)
        ]

    def _sanitize_content(self, content: str) -> str:
        if len(content) <= self.max_content_chars:
            return content
        return f"{content[: self.max_content_chars]}[truncated]"

    def _sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in metadata.items()
            if key.lower() not in SENSITIVE_METADATA_KEYS
        }

