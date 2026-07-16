from collections.abc import Callable
from dataclasses import replace
from typing import Any

from agent.context import AgentContext
from agent.context import ContextManager
from agent.events import EventBus
from agent.schemas import AgentEvent
from agent.schemas import AgentEventType
from agent.schemas import AgentRequest
from agent.schemas import AgentResult
from agent.schemas import AgentStatus

WorkflowHandler = Callable[[AgentRequest, AgentContext], AgentResult]


class AgentRuntime:
    def __init__(
        self,
        context_manager: ContextManager | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.context_manager = context_manager or ContextManager()
        self.event_bus = event_bus or EventBus()
        self._workflows: dict[str, WorkflowHandler] = {}

    def register_workflow(self, task_type: str, handler: WorkflowHandler) -> None:
        self._workflows[task_type] = handler

    def run(
        self,
        request: AgentRequest,
        recent_messages: list[dict[str, Any]] | None = None,
        variables: dict[str, Any] | None = None,
    ) -> AgentResult:
        start_event = AgentEvent(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            event_type=AgentEventType.STARTED,
            message="Agent runtime started.",
            progress=0,
        )
        self.event_bus.publish(start_event)

        context = self.context_manager.build_context(
            request=request,
            recent_messages=recent_messages,
            variables=variables,
        )

        handler = self._workflows.get(request.task_type)
        if handler is None:
            return self._fail(
                request=request,
                message=f"No workflow registered for task_type: {request.task_type}",
                events=[start_event],
            )

        try:
            result = handler(request, context)
        except Exception as exc:
            return self._fail(request=request, message=str(exc), events=[start_event])

        completed_event = AgentEvent(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            event_type=AgentEventType.COMPLETED,
            message="Agent runtime completed.",
            progress=100,
        )
        self.event_bus.publish(completed_event)

        return replace(
            result,
            status=AgentStatus.SUCCEEDED,
            events=[*result.events, start_event, completed_event],
        )

    def _fail(
        self,
        request: AgentRequest,
        message: str,
        events: list[AgentEvent],
    ) -> AgentResult:
        failed_event = AgentEvent(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            event_type=AgentEventType.FAILED,
            message=message,
            progress=100,
        )
        self.event_bus.publish(failed_event)
        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.FAILED,
            title=request.title or request.query_or_topic,
            content={"error": message},
            markdown=message,
            warnings=[message],
            events=[*events, failed_event],
        )
