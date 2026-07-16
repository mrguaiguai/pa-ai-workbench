from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from typing import Any


class ChatMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ChatMessage:
    role: ChatMessageRole | str
    content: str

    def __post_init__(self) -> None:
        if isinstance(self.role, str):
            object.__setattr__(self, "role", ChatMessageRole(self.role))
        if not isinstance(self.content, str):
            raise TypeError("ChatMessage.content must be a string")


@dataclass(frozen=True)
class ChatRequest:
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_messages = [
            message if isinstance(message, ChatMessage) else ChatMessage(**message)
            for message in self.messages
        ]
        object.__setattr__(self, "messages", normalized_messages)
        if not normalized_messages:
            raise ValueError("ChatRequest.messages must not be empty")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("ChatRequest.max_tokens must be positive when set")
        if self.temperature < 0:
            raise ValueError("ChatRequest.temperature must be non-negative")


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider:
            raise ValueError("ChatResponse.provider must not be empty")
        if not self.model:
            raise ValueError("ChatResponse.model must not be empty")
        if not isinstance(self.content, str):
            raise TypeError("ChatResponse.content must be a string")
