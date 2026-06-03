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


class CaseReviewWorkflow:
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
                step="retrieve_case_evidence",
                message="Retrieving case evidence.",
                progress=25,
            )
        ]

        citations = self._retrieve_citations(request)
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="retrieve_case_evidence",
                message=f"Retrieved {len(citations)} case evidence item(s).",
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
                    step="case_review",
                    message="Case review completed with warnings.",
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
            warnings.append("No case evidence was found for the review.")
        return warnings

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.business_area:
            filters["business_area"] = request.business_area
        filters["document_type"] = request.document_type or "case"
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
                "excerpt": CaseReviewWorkflow._excerpt(citation.text),
                "score": citation.score,
            }
            for citation in citations
        ]
        relevant_facts = [
            f"证据 {index}：{summary['excerpt']}"
            for index, summary in enumerate(evidence_summaries, start=1)
        ]
        if not relevant_facts:
            relevant_facts = ["当前证据不足，暂无法提炼可靠事实。"]

        return {
            "case_summary": (
                f"围绕“{request.query_or_topic}”完成轻量案例复盘，"
                f"共引用 {len(citations)} 条证据。"
            ),
            "relevant_facts": relevant_facts,
            "issues_and_risks": [
                "需核对案例时间线、责任边界和对外沟通动作是否完整。",
                "如证据不足，应避免形成确定性判断。",
            ],
            "suggested_next_checks": [
                "补充原始案例材料、时间线记录和关键沟通纪要。",
                "确认是否存在缺失证据、相互矛盾证据或未覆盖的相关方。",
            ],
            "evidence": evidence_summaries,
            "recent_message_count": len(context.recent_messages),
            "filters": CaseReviewWorkflow._build_filters(request),
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
            "### 案例摘要",
            content["case_summary"],
            "",
        ]

        if request.extra_requirements:
            lines.extend(["### 复盘要求", request.extra_requirements, ""])

        lines.extend(["### 相关事实"])
        lines.extend(f"- {item}" for item in content["relevant_facts"])
        lines.append("")

        lines.extend(["### 问题与风险"])
        lines.extend(f"- {item}" for item in content["issues_and_risks"])
        lines.append("")

        lines.extend(["### 建议补充核查"])
        lines.extend(f"- {item}" for item in content["suggested_next_checks"])

        if citations:
            lines.extend(["", "### 证据摘录"])
            for index, citation in enumerate(citations, start=1):
                lines.append(
                    f"{index}. {citation.title}："
                    f"{CaseReviewWorkflow._excerpt(citation.text)} "
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

