from typing import Any

from agent.agents import CaseReviewWorkflow
from agent.agents import KnowledgeQaWorkflow
from agent.agents import PolicyAnalysisWorkflow
from agent.context import ContextManager
from agent.events import EventBus
from agent.runtime import AgentRuntime
from agent.schemas import AgentRequest
from agent.schemas import AgentResult
from agent.schemas import AgentTaskType


class AgentOrchestrator:
    def __init__(
        self,
        runtime: AgentRuntime | None = None,
        context_manager: ContextManager | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.runtime = runtime or AgentRuntime(
            context_manager=context_manager,
            event_bus=event_bus,
        )
        self._register_builtin_workflows()

    def run(
        self,
        request: AgentRequest,
        recent_messages: list[dict[str, Any]] | None = None,
        variables: dict[str, Any] | None = None,
    ) -> AgentResult:
        return self.runtime.run(
            request=request,
            recent_messages=recent_messages,
            variables=variables,
        )

    def _register_builtin_workflows(self) -> None:
        self.runtime.register_workflow(
            AgentTaskType.KNOWLEDGE_QA,
            KnowledgeQaWorkflow(),
        )
        self.runtime.register_workflow(
            AgentTaskType.POLICY_ANALYSIS,
            PolicyAnalysisWorkflow(),
        )
        self.runtime.register_workflow(
            AgentTaskType.CASE_REVIEW,
            CaseReviewWorkflow(),
        )

