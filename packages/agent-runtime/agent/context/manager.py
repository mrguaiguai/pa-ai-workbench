from dataclasses import dataclass
from dataclasses import field
from typing import Any

from agent.schemas import AgentRequest


@dataclass(frozen=True)
class AgentContext:
    request: AgentRequest
    recent_messages: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)


class ContextManager:
    def build_context(
        self,
        request: AgentRequest,
        recent_messages: list[dict[str, Any]] | None = None,
        variables: dict[str, Any] | None = None,
    ) -> AgentContext:
        return AgentContext(
            request=request,
            recent_messages=list(recent_messages or []),
            variables=dict(variables or {}),
        )

