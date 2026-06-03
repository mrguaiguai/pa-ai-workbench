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


class PolicyAnalysisWorkflow:
    def __init__(
        self,
        retriever: RetrieverTool | None = None,
        citation_checker: CitationChecker | None = None,
        top_k: int = 6,
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
                step="retrieve_policy_evidence",
                message="Retrieving policy evidence.",
                progress=25,
            )
        ]

        citations = self._retrieve_citations(request)
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="retrieve_policy_evidence",
                message=f"Retrieved {len(citations)} policy evidence item(s).",
                progress=55,
                payload={"citation_count": len(citations)},
            )
        )

        warnings = self._build_warnings(citations)
        if warnings:
            events.append(
                AgentEvent(
                    task_id=request.task_id,
                    conversation_id=request.conversation_id,
                    event_type=AgentEventType.WARNING,
                    step="policy_analysis",
                    message="Policy analysis completed with warnings.",
                    progress=80,
                    payload={"warnings": warnings},
                )
            )

        content = self._build_content(request, context, citations, warnings)
        markdown = self._build_markdown(request, content, citations, warnings)
        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.RUNNING,
            title=request.title or request.query_or_topic,
            content=content,
            markdown=markdown,
            citations=citations,
            warnings=warnings,
            memory_updates=[
                {
                    "role": "assistant",
                    "content": markdown,
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

    def _build_warnings(self, citations: list[Citation]) -> list[str]:
        check_result = self.citation_checker.validate(citations)
        warnings = list(check_result.warnings)
        if not citations:
            warnings.append("No policy evidence was found for the analysis.")
        return warnings

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.business_area:
            filters["business_area"] = request.business_area
        filters["document_type"] = request.document_type or "policy"
        return filters

    @staticmethod
    def _build_content(
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
        warnings: list[str],
    ) -> dict[str, Any]:
        evidence_summaries = [
            {
                "title": citation.title,
                "source": citation.source,
                "excerpt": PolicyAnalysisWorkflow._excerpt(citation.text),
                "score": citation.score,
            }
            for citation in citations
        ]
        key_requirements = [
            f"关注证据 {index} 中提到的要求或变化：{summary['excerpt']}"
            for index, summary in enumerate(evidence_summaries, start=1)
        ]
        if not key_requirements:
            key_requirements = ["当前证据不足，暂无法提炼明确政策要求。"]

        return {
            "executive_summary": (
                f"围绕“{request.query_or_topic}”完成政策分析初稿，"
                f"共引用 {len(citations)} 条证据。"
            ),
            "key_requirements": key_requirements,
            "impact_and_risks": [
                "需结合业务场景评估政策要求对流程、口径和外部沟通的影响。",
                "如证据不足或存在冲突，应先补充资料后再形成正式结论。",
            ],
            "recommended_actions": [
                "补充最新政策原文或权威解读材料。",
                "将关键要求映射到责任部门、时间节点和对外沟通口径。",
            ],
            "evidence": evidence_summaries,
            "recent_message_count": len(context.recent_messages),
            "filters": PolicyAnalysisWorkflow._build_filters(request),
            "warnings": warnings,
        }

    @staticmethod
    def _build_markdown(
        request: AgentRequest,
        content: dict[str, Any],
        citations: list[Citation],
        warnings: list[str],
    ) -> str:
        lines = [
            f"## {request.title or request.query_or_topic}",
            "",
            "### 摘要",
            content["executive_summary"],
            "",
        ]

        if request.extra_requirements:
            lines.extend(["### 补充要求", request.extra_requirements, ""])

        lines.extend(["### 关键要求或变化"])
        lines.extend(f"- {item}" for item in content["key_requirements"])
        lines.append("")

        lines.extend(["### 影响与风险"])
        lines.extend(f"- {item}" for item in content["impact_and_risks"])
        lines.append("")

        lines.extend(["### 建议动作"])
        lines.extend(f"- {item}" for item in content["recommended_actions"])

        if citations:
            lines.extend(["", "### 证据摘录"])
            for index, citation in enumerate(citations, start=1):
                lines.append(
                    f"{index}. {citation.title}："
                    f"{PolicyAnalysisWorkflow._excerpt(citation.text)} "
                    f"[来源：{citation.source}]"
                )

        if warnings:
            lines.extend(["", "### 注意事项"])
            lines.extend(f"- {warning}" for warning in warnings)

        return "\n".join(lines)

    @staticmethod
    def _excerpt(text: str, max_chars: int = 280) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[:max_chars]}[truncated]"

