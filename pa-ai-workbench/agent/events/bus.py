from collections.abc import Callable

from agent.schemas import AgentEvent

EventHandler = Callable[[AgentEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self._events: list[AgentEvent] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def publish(self, event: AgentEvent) -> None:
        self._events.append(event)
        for handler in self._handlers:
            handler(event)

    def list_events(self) -> list[AgentEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()

