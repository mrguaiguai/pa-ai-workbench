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
from agent.tools.evidence_policy import EvidencePolicy
from agent.tools.evidence_policy import EvidencePolicyResult


class CaseReviewWorkflow:
    def __init__(
        self,
        retriever: RetrieverTool | None = None,
        citation_checker: CitationChecker | None = None,
        model_gateway: ModelGateway | None = None,
        evidence_policy: EvidencePolicy | None = None,
        top_k: int = 6,
    ) -> None:
        self.retriever = retriever or RetrieverTool()
        self.citation_checker = citation_checker or CitationChecker()
        self.model_gateway = model_gateway or get_model_gateway()
        self.evidence_policy = evidence_policy or EvidencePolicy(self.citation_checker)
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

        retrieved_citations = self._retrieve_citations(request)
        policy_result = self.evidence_policy.evaluate(
            retrieved_citations,
            workflow="case review",
            expected_source_type=self._expected_source_type(request),
        )
        citations = policy_result.citations
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="retrieve_case_evidence",
                message=f"Retrieved {len(citations)} usable case evidence item(s).",
                progress=55,
                payload={
                    "citation_count": len(citations),
                    "retrieved_count": len(retrieved_citations),
                    "warning_codes": policy_result.warning_codes,
                },
            )
        )

        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_STARTED,
                step="generate_case_review",
                message="Generating grounded case review through ModelGateway.",
                progress=65,
                payload={"citation_count": len(citations)},
            )
        )
        markdown, model_metadata = self._generate_review(
            request,
            context,
            citations,
            policy_result,
        )
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="generate_case_review",
                message="Generated grounded case review.",
                progress=75,
                payload=model_metadata,
            )
        )

        warnings = list(policy_result.warnings)
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

        content = self._build_content(
            request=request,
            context=context,
            citations=citations,
            warnings=warnings,
            markdown=markdown,
            model_metadata=model_metadata,
            policy_result=policy_result,
            retrieved_citation_count=len(retrieved_citations),
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

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.business_area:
            filters["business_area"] = request.business_area
        if request.document_type:
            filters["document_type"] = request.document_type
        return filters

    @staticmethod
    def _expected_source_type(request: AgentRequest) -> str | None:
        return request.metadata.get("expected_source_type") or request.metadata.get(
            "required_source_type"
        )

    def _generate_review(
        self,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
        policy_result: EvidencePolicyResult,
    ) -> tuple[str, dict[str, Any]]:
        response = self.model_gateway.generate(
            ChatRequest(
                messages=self._build_messages(request, context, citations),
                temperature=0.2,
                max_tokens=1800,
                metadata={
                    "task_id": request.task_id,
                    "task_type": request.task_type,
                    "workflow": "case_review",
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
            "warning_codes": policy_result.warning_codes,
            "weak_evidence_count": policy_result.weak_evidence_count,
            "dropped_citation_count": policy_result.dropped_citation_count,
            "source_type_mismatch_count": policy_result.source_type_mismatch_count,
        }
        return self._grounded_markdown(
            response.content,
            request,
            citations,
            policy_result,
        ), metadata

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
                    "你是 PA 智能工作台的案例复盘助手。必须基于给定案例、文档或 "
                    "Wiki 证据输出复盘；不得编造来源。输出中文 Markdown，包含："
                    "案例摘要、相关事实、问题与风险、建议补充核查、证据缺口。"
                    "所有案例事实和时间线判断必须使用 [1] 这样的证据编号。"
                    "证据不足时，只能列出待补材料，不要编造案例细节。"
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
            f"案例复盘主题：{request.query_or_topic}",
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
            lines.extend(["复盘要求：", request.extra_requirements, ""])

        if citations:
            lines.extend(["证据：", ""])
            for index, citation in enumerate(citations, start=1):
                lines.extend(cls._citation_prompt_lines(index, citation))
        else:
            lines.append("证据：未检索到可用案例、文档或 Wiki 证据。")

        lines.extend(
            [
                "",
                "请输出以下结构：",
                "1. 案例摘要，所有事实判断都使用 [1] 这样的证据编号",
                "2. 相关事实或时间线，逐条标注证据编号、evidence_id、source_type",
                "3. 问题与风险，明确对应证据编号",
                "4. 建议补充核查，区分已由证据支持和需要补充确认的事项",
                "5. 证据缺口或不确定性",
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
        policy_result: EvidencePolicyResult,
        retrieved_citation_count: int,
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
        relevant_facts = [
            f"证据 {index}：{summary['excerpt']}"
            for index, summary in enumerate(evidence_summaries, start=1)
        ]
        if not relevant_facts:
            relevant_facts = ["当前证据不足，暂无法提炼可靠事实。"]

        return {
            "review": markdown,
            "case_summary": (
                f"围绕“{request.query_or_topic}”通过 ModelGateway 完成案例复盘，"
                f"共引用 {len(citations)} 条证据。"
            ),
            "relevant_facts": relevant_facts,
            "issues_and_risks": [
                "模型复盘已在 markdown 中展开；正式结论仍需核对时间线与责任边界。",
                "如证据不足、冲突或缺少关键相关方，应避免形成确定性判断。",
            ],
            "suggested_next_checks": [
                "复核模型输出中的证据编号是否覆盖关键事实。",
                "补充原始案例材料、时间线记录、关键沟通纪要和相关方反馈。",
            ],
            "citation_count": len(citations),
            "retrieved_citation_count": retrieved_citation_count,
            "evidence": evidence_summaries,
            "recent_message_count": len(context.recent_messages),
            "filters": cls._build_filters(request),
            "model": model_metadata,
            "warnings": warnings,
            "warning_codes": policy_result.warning_codes,
            "evidence_quality": cls._evidence_quality(policy_result),
        }

    @staticmethod
    def _evidence_quality(policy_result: EvidencePolicyResult) -> dict[str, Any]:
        return {
            "mode": policy_result.evidence_mode,
            "weak_evidence_count": policy_result.weak_evidence_count,
            "dropped_citation_count": policy_result.dropped_citation_count,
            "source_type_mismatch_count": policy_result.source_type_mismatch_count,
            "warning_codes": policy_result.warning_codes,
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
        review: str,
        request: AgentRequest,
        citations: list[Citation],
        policy_result: EvidencePolicyResult,
    ) -> str:
        if not citations:
            return "\n".join(
                [
                    "## 依据不足",
                    "",
                    f"未检索到与“{request.query_or_topic}”相关的案例、文档或 Wiki 证据，无法形成案例复盘。",
                    "",
                    "## 待补材料",
                    "",
                    "- 补充原始案例材料、时间线记录、关键沟通纪要或已发布 Wiki 页面后重试。",
                    "- 确认资料已完成 WeKnora 索引，并检查检索条件是否过窄。",
                ]
            )

        lines = [
            review.strip(),
            "",
            "## 事实与引用",
            "",
            *[
                cls._case_fact_line(index, citation)
                for index, citation in enumerate(citations, start=1)
            ],
            "",
            "## 待补材料与不确定性",
            "",
            "- 以上复盘只覆盖已检索到的证据；时间线、责任边界和相关方反馈仍需人工复核。",
            "- 如缺少原始记录、关键节点或后续处置材料，应补充后再形成正式复盘。",
        ]
        lines.extend(cls._quality_warning_lines(policy_result))
        return "\n".join(lines).strip()

    @staticmethod
    def _quality_warning_lines(policy_result: EvidencePolicyResult) -> list[str]:
        lines: list[str] = []
        if "WEAK_EVIDENCE" in policy_result.warning_codes:
            lines.extend(
                [
                    "",
                    "## 证据质量提示",
                    "",
                    "- 检索到低置信 evidence，案例事实和风险判断应标记为不确定。",
                ]
            )
        if "SOURCE_TYPE_MISMATCH" in policy_result.warning_codes:
            if not lines:
                lines.extend(["", "## 证据质量提示", ""])
            lines.append("- 部分 evidence 的 source_type 不符合请求范围，已从引用中排除。")
        return lines

    @classmethod
    def _case_fact_line(cls, index: int, citation: Citation) -> str:
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
