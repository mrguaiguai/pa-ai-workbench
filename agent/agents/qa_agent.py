from typing import Any

from agent.context import AgentContext
from agent.schemas import AgentEvent
from agent.schemas import AgentEventType
from agent.schemas import AgentRequest
from agent.schemas import AgentResult
from agent.schemas import AgentStatus
from agent.schemas import Citation
from agent.tools import CitationChecker
from agent.tools import RetrieverTool


class KnowledgeQaWorkflow:
    def __init__(
        self,
        retriever: RetrieverTool | None = None,
        citation_checker: CitationChecker | None = None,
        top_k: int = 5,
    ) -> None:
        self.retriever = retriever or RetrieverTool()
        self.citation_checker = citation_checker or CitationChecker()
        self.top_k = top_k

    def __call__(self, request: AgentRequest, context: AgentContext) -> AgentResult:
        events = [
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_STARTED,
                step="retrieve",
                message="Retrieving evidence for knowledge QA.",
                progress=25,
            )
        ]

        citations = self._retrieve_citations(request)
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="retrieve",
                message=f"Retrieved {len(citations)} evidence item(s).",
                progress=60,
                payload={"citation_count": len(citations)},
            )
        )

        check_result = self.citation_checker.validate(citations)
        warnings = list(check_result.warnings)
        if not citations:
            warnings.append("No evidence was found for the question.")

        if warnings:
            events.append(
                AgentEvent(
                    task_id=request.task_id,
                    conversation_id=request.conversation_id,
                    event_type=AgentEventType.WARNING,
                    step="citation_check",
                    message="Knowledge QA completed with warnings.",
                    progress=80,
                    payload={"warnings": warnings},
                )
            )

        answer = self._build_answer(request, context, citations, warnings)
        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.RUNNING,
            title=request.title or request.query_or_topic,
            content={
                "answer": answer,
                "citation_count": len(citations),
                "recent_message_count": len(context.recent_messages),
                "filters": self._build_filters(request),
            },
            markdown=answer,
            citations=citations,
            warnings=warnings,
            memory_updates=[
                {
                    "role": "assistant",
                    "content": answer,
                    "metadata": {
                        "task_id": request.task_id,
                        "task_type": request.task_type,
                        "citation_count": len(citations),
                    },
                }
            ],
            events=events,
        )

    def _retrieve_citations(self, request: AgentRequest) -> list[Citation]:
        citations = self.retriever.retrieve(
            query=request.query_or_topic,
            filters=self._build_filters(request),
            top_k=self.top_k,
        )
        if not request.document_ids:
            return citations
        scoped_document_ids = set(request.document_ids)
        return [
            citation
            for citation in citations
            if citation.document_id in scoped_document_ids
            or citation.external_doc_id in scoped_document_ids
        ]

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.business_area:
            filters["business_area"] = request.business_area
        if request.document_type:
            filters["document_type"] = request.document_type
        return filters

    @staticmethod
    def _build_answer(
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
        warnings: list[str],
    ) -> str:
        lines = [
            f"## {request.title or request.query_or_topic}",
            "",
            f"问题：{request.query_or_topic}",
            "",
        ]

        if context.recent_messages:
            lines.extend(
                [
                    f"已参考最近 {len(context.recent_messages)} 条会话上下文。",
                    "",
                ]
            )

        if request.extra_requirements:
            lines.extend(["补充要求：", request.extra_requirements, ""])

        if citations:
            lines.extend(["基于当前知识库证据，可以先形成以下回答：", ""])
            for index, citation in enumerate(citations, start=1):
                evidence_excerpt = KnowledgeQaWorkflow._excerpt(citation.text)
                lines.append(
                    f"{index}. {citation.title}：{evidence_excerpt} "
                    f"[来源：{citation.source}]"
                )
            lines.append("")
            lines.append("以上结论仅基于已检索到的证据，后续可继续补充材料再细化。")
        else:
            lines.append("当前没有检索到足够证据，建议补充资料或放宽筛选条件后再分析。")

        if warnings:
            lines.extend(["", "注意事项："])
            lines.extend(f"- {warning}" for warning in warnings)

        return "\n".join(lines)

    @staticmethod
    def _excerpt(text: str, max_chars: int = 280) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[:max_chars]}[truncated]"
