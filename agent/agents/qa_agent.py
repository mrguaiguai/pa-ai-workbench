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


class KnowledgeQaWorkflow:
    def __init__(
        self,
        retriever: RetrieverTool | None = None,
        citation_checker: CitationChecker | None = None,
        model_gateway: ModelGateway | None = None,
        top_k: int = 5,
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
        answer, model_metadata = self._generate_answer(request, context, citations)
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

        check_result = self.citation_checker.validate(
            citations,
            evidence_items=citations,
        )
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
                "model": model_metadata,
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

    def _generate_answer(
        self,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
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
        }
        return response.content, metadata

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
                    "并在涉及事实判断时引用证据编号。不得编造未给出的来源。"
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
                "1. 直接回答",
                "2. 依据列表，逐条标注使用的证据编号",
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
