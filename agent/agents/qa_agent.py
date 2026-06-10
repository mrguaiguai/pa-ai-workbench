import time
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


class KnowledgeQaWorkflow:
    def __init__(
        self,
        retriever: RetrieverTool | None = None,
        citation_checker: CitationChecker | None = None,
        model_gateway: ModelGateway | None = None,
        evidence_policy: EvidencePolicy | None = None,
        top_k: int = 5,
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
                step="retrieve",
                message="Retrieving evidence for knowledge QA.",
                progress=25,
            )
        ]

        retrieved_citations = self._retrieve_citations(request)
        policy_result = self.evidence_policy.evaluate(
            retrieved_citations,
            workflow="knowledge question",
            expected_source_type=self._expected_source_type(request),
        )
        citations = policy_result.citations
        events.append(
            AgentEvent(
                task_id=request.task_id,
                conversation_id=request.conversation_id,
                event_type=AgentEventType.STEP_COMPLETED,
                step="retrieve",
                message=f"Retrieved {len(citations)} usable evidence item(s).",
                progress=60,
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
                step="generate",
                message="Generating grounded QA answer through ModelGateway.",
                progress=65,
                payload={"citation_count": len(citations)},
            )
        )
        answer, model_metadata = self._generate_answer(
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
                step="generate",
                message="Generated grounded QA answer.",
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
                    step="citation_check",
                    message="Knowledge QA completed with warnings.",
                    progress=80,
                    payload={"warnings": warnings},
                )
            )

        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.RUNNING,
            title=request.title or request.query_or_topic,
            content={
                "answer": answer,
                "citation_count": len(citations),
                "retrieved_citation_count": len(retrieved_citations),
                "recent_message_count": len(context.recent_messages),
                "filters": self._build_filters(request),
                "model": model_metadata,
                "warning_codes": policy_result.warning_codes,
                "evidence_quality": self._evidence_quality(policy_result),
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
        scoped = self._scope_citations(citations, request.document_ids)
        if scoped:
            return scoped
        return self._retrieve_scoped_retry(request)

    def _retrieve_scoped_retry(self, request: AgentRequest) -> list[Citation]:
        for attempt in range(3):
            retry_citations = self.retriever.retrieve(
                query=request.query_or_topic,
                filters={"document_ids": request.document_ids},
                top_k=self.top_k,
            )
            scoped = self._scope_citations(retry_citations, request.document_ids)
            if scoped or attempt == 2:
                return scoped
            time.sleep(2)
        return []

    @staticmethod
    def _scope_citations(
        citations: list[Citation],
        document_ids: list[str],
    ) -> list[Citation]:
        scoped_document_ids = set(document_ids)
        return [
            citation
            for citation in citations
            if citation.document_id in scoped_document_ids
            or citation.external_doc_id in scoped_document_ids
        ]

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.document_ids:
            filters["document_ids"] = request.document_ids
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

    def _generate_answer(
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
                max_tokens=1600,
                metadata={
                    "task_id": request.task_id,
                    "task_type": request.task_type,
                    "workflow": "knowledge_qa",
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
        return self._grounded_markdown(response.content, citations, policy_result), metadata

    @staticmethod
    def _evidence_quality(policy_result: EvidencePolicyResult) -> dict[str, Any]:
        return {
            "mode": policy_result.evidence_mode,
            "weak_evidence_count": policy_result.weak_evidence_count,
            "dropped_citation_count": policy_result.dropped_citation_count,
            "source_type_mismatch_count": policy_result.source_type_mismatch_count,
            "warning_codes": policy_result.warning_codes,
        }

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
                    "你是 PA 智能工作台的知识问答助手。必须只基于给定证据回答；"
                    "如果证据不足，要明确说明不足。回答使用中文 Markdown，"
                    "并在涉及事实判断时使用 [1] 这样的证据编号。不得编造未给出的来源。"
                    "如果没有可用证据，只能说明依据不足，不要给出事实性结论。"
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
            lines.extend(["证据：", ""])
            for index, citation in enumerate(citations, start=1):
                lines.extend(cls._citation_prompt_lines(index, citation))
        else:
            lines.append("证据：未检索到可用证据。")

        lines.extend(
            [
                "",
                "请输出：",
                "1. 直接回答，所有事实判断都用 [1] 这样的证据编号",
                "2. 依据列表，逐条标注使用的证据编号、evidence_id、source_type",
                "3. 证据不足或不确定之处",
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

    @staticmethod
    def _excerpt(text: str, max_chars: int = 280) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[:max_chars]}[truncated]"

    @classmethod
    def _grounded_markdown(
        cls,
        answer: str,
        citations: list[Citation],
        policy_result: EvidencePolicyResult,
    ) -> str:
        if not citations:
            return "\n".join(
                [
                    "## 依据不足",
                    "",
                    "未检索到可用证据，无法基于 WeKnora evidence 回答该问题。",
                    "请补充资料、调整问题，或确认知识库索引状态后重试。",
                ]
            )
        lines = [
            answer.strip(),
            "",
            "## 引用证据",
            "",
            *[
                cls._citation_markdown_line(index, citation)
                for index, citation in enumerate(citations, start=1)
            ],
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
                    "- 检索到低置信 evidence，相关结论应标记为不确定，并在补充资料后复核。",
                ]
            )
        if "SOURCE_TYPE_MISMATCH" in policy_result.warning_codes:
            if not lines:
                lines.extend(["", "## 证据质量提示", ""])
            lines.append("- 部分 evidence 的 source_type 不符合请求范围，已从引用中排除。")
        return lines

    @classmethod
    def _citation_markdown_line(cls, index: int, citation: Citation) -> str:
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
        return f"- [{index}] {citation.title} ({'; '.join(identifiers)})"

    @staticmethod
    def _evidence_mode(citations: list[Citation]) -> str:
        if not citations:
            return "no_evidence"
        if all(citation.source == "weknora_api" for citation in citations):
            return "weknora_api"
        return "mixed"
