from typing import Any

from agent.context import AgentContext
from agent.model_gateway import ChatMessage
from agent.model_gateway import ChatMessageRole
from agent.model_gateway import ChatRequest
from agent.model_gateway import ModelGateway
from agent.model_gateway import get_model_gateway
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
        model_gateway: ModelGateway | None = None,
        top_k: int = 6,
    ) -> None:
        self.retriever = retriever or RetrieverTool()
        self.citation_checker = citation_checker or CitationChecker()
        self.model_gateway = model_gateway or get_model_gateway()
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

        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_STARTED,
                step="generate_policy_analysis",
                message="Generating grounded policy analysis through ModelGateway.",
                progress=65,
                payload={"citation_count": len(citations)},
            )
        )
        markdown, model_metadata = self._generate_analysis(request, context, citations)
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="generate_policy_analysis",
                message="Generated grounded policy analysis.",
                progress=75,
                payload=model_metadata,
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

        content = self._build_content(
            request=request,
            context=context,
            citations=citations,
            warnings=warnings,
            markdown=markdown,
            model_metadata=model_metadata,
        )
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
        check_result = self.citation_checker.validate(
            citations,
            evidence_items=citations,
        )
        warnings = list(check_result.warnings)
        if not citations:
            warnings.append("No policy evidence was found for the analysis.")
        return warnings

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.business_area:
            filters["business_area"] = request.business_area
        if request.document_type:
            filters["document_type"] = request.document_type
        return filters

    def _generate_analysis(
        self,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
    ) -> tuple[str, dict[str, Any]]:
        response = self.model_gateway.generate(
            ChatRequest(
                messages=self._build_messages(request, context, citations),
                temperature=0.2,
                max_tokens=1800,
                metadata={
                    "task_id": request.task_id,
                    "task_type": request.task_type,
                    "workflow": "policy_analysis",
                    "citation_count": len(citations),
                    "source_types": sorted(
                        {citation.source_type or "unknown" for citation in citations}
                    ),
                },
            )
        )
        metadata = {
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "evidence_sources": sorted({citation.source for citation in citations}),
            "source_types": sorted(
                {citation.source_type or "unknown" for citation in citations}
            ),
            "evidence_mode": self._evidence_mode(citations),
        }
        return self._grounded_markdown(response.content, request, citations), metadata

    @classmethod
    def _build_messages(
        cls,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
    ) -> list[ChatMessage]:
        return [
            ChatMessage(
                role=ChatMessageRole.SYSTEM,
                content=(
                    "你是 PA 智能工作台的政策分析助手。必须基于给定政策、案例或 "
                    "Wiki 证据输出分析；不得编造来源。输出中文 Markdown，包含："
                    "摘要、关键要求或变化、影响与风险、建议动作、不确定性。"
                    "关键判断必须使用 [1] 这样的证据编号。证据不足时，只能列出"
                    "待补证据，不要给出事实性政策结论。"
                ),
            ),
            ChatMessage(
                role=ChatMessageRole.USER,
                content=cls._build_grounded_prompt(request, context, citations),
            ),
        ]

    @classmethod
    def _build_grounded_prompt(
        cls,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
    ) -> str:
        lines = [
            f"政策分析主题：{request.query_or_topic}",
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
            lines.extend(["证据：", ""])
            for index, citation in enumerate(citations, start=1):
                lines.extend(cls._citation_prompt_lines(index, citation))
        else:
            lines.append("证据：未检索到可用政策、案例或 Wiki 证据。")

        lines.extend(
            [
                "",
                "请输出以下结构：",
                "1. 摘要，所有关键判断都使用 [1] 这样的证据编号",
                "2. 关键要求或变化，逐条标注证据编号、evidence_id、source_type",
                "3. 影响与风险，明确对应证据编号",
                "4. 建议动作，区分已由证据支持和需要业务确认的动作",
                "5. 不确定性与待补证据",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _citation_prompt_lines(cls, index: int, citation: Citation) -> list[str]:
        source_type = citation.source_type or citation.metadata.get(
            "citation_source_type"
        )
        evidence_id = citation.evidence_id or citation.metadata.get("evidence_id")
        identifiers = [
            f"source_type={source_type or 'unknown'}",
            f"evidence_id={evidence_id or 'unknown'}",
        ]
        if citation.document_id:
            identifiers.append(f"document_id={citation.document_id}")
        if citation.external_doc_id:
            identifiers.append(f"external_doc_id={citation.external_doc_id}")
        if citation.chunk_id:
            identifiers.append(f"chunk_id={citation.chunk_id}")
        if citation.wiki_page_id:
            identifiers.append(f"wiki_page_id={citation.wiki_page_id}")
        return [
            f"[{index}] {citation.title}",
            f"- {'; '.join(identifiers)}",
            f"- source={citation.source}; score={citation.score}",
            f"- excerpt={cls._excerpt(citation.text)}",
            "",
        ]

    @classmethod
    def _build_content(
        cls,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
        warnings: list[str],
        markdown: str,
        model_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        evidence_summaries = [
            {
                "title": citation.title,
                "source": citation.source,
                "excerpt": cls._excerpt(citation.text),
                "score": citation.score,
                "evidence_id": citation.evidence_id,
                "source_type": citation.source_type,
                "chunk_id": citation.chunk_id,
                "wiki_page_id": citation.wiki_page_id,
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
            "analysis": markdown,
            "executive_summary": (
                f"围绕“{request.query_or_topic}”通过 ModelGateway 完成政策分析，"
                f"共引用 {len(citations)} 条证据。"
            ),
            "key_requirements": key_requirements,
            "impact_and_risks": [
                "模型分析已在 markdown 中展开；正式结论仍需结合业务场景复核。",
                "如证据不足或存在冲突，应先补充资料后再形成正式口径。",
            ],
            "recommended_actions": [
                "复核模型输出中的证据编号是否覆盖关键判断。",
                "将建议动作映射到责任部门、时间节点和对外沟通口径。",
            ],
            "citation_count": len(citations),
            "evidence": evidence_summaries,
            "recent_message_count": len(context.recent_messages),
            "filters": cls._build_filters(request),
            "model": model_metadata,
            "warnings": warnings,
        }

    @staticmethod
    def _excerpt(text: str, max_chars: int = 280) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[:max_chars]}[truncated]"

    @classmethod
    def _grounded_markdown(
        cls,
        analysis: str,
        request: AgentRequest,
        citations: list[Citation],
    ) -> str:
        if not citations:
            return "\n".join(
                [
                    "## 依据不足",
                    "",
                    f"未检索到与“{request.query_or_topic}”相关的政策、案例或 Wiki 证据，无法形成政策判断。",
                    "",
                    "## 待补证据",
                    "",
                    "- 补充适用政策原文、案例材料或已发布 Wiki 页面后重试。",
                    "- 确认资料已完成 WeKnora 索引，并检查检索条件是否过窄。",
                ]
            )

        return "\n".join(
            [
                analysis.strip(),
                "",
                "## 关键判断与引用",
                "",
                *[
                    cls._policy_judgment_line(index, citation)
                    for index, citation in enumerate(citations, start=1)
                ],
                "",
                "## 不确定性与待补证据",
                "",
                "- 以上判断只覆盖已检索到的证据；正式口径仍需业务负责人复核。",
                "- 如存在适用范围、发布日期、案例背景或执行口径缺口，应补充对应材料后再定稿。",
            ]
        ).strip()

    @classmethod
    def _policy_judgment_line(cls, index: int, citation: Citation) -> str:
        source_type = citation.source_type or citation.metadata.get(
            "citation_source_type"
        )
        evidence_id = citation.evidence_id or citation.metadata.get("evidence_id")
        identifiers = [
            f"source_type={source_type or 'unknown'}",
            f"evidence_id={evidence_id or 'unknown'}",
        ]
        if citation.chunk_id:
            identifiers.append(f"chunk_id={citation.chunk_id}")
        if citation.wiki_page_id:
            identifiers.append(f"wiki_page_id={citation.wiki_page_id}")
        return (
            f"- [{index}] {citation.title}: {cls._excerpt(citation.text, max_chars=140)} "
            f"({'; '.join(identifiers)})"
        )

    @staticmethod
    def _evidence_mode(citations: list[Citation]) -> str:
        if not citations:
            return "no_evidence"
        if all(citation.source == "weknora_api" for citation in citations):
            return "weknora_api"
        return "mixed"
