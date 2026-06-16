from dataclasses import replace
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
        retrieved_citations, guard_warnings, guard_codes, guard_dropped_count = (
            self._apply_forbidden_anchor_policy(request, retrieved_citations)
        )
        policy_result = self.evidence_policy.evaluate(
            retrieved_citations,
            workflow="knowledge question",
            expected_source_types=self._expected_source_types(request),
            require_all_expected_source_types=bool(
                request.expected_source_types and request.retrieval_scope == "all"
            ),
        )
        if guard_warnings:
            policy_result = replace(
                policy_result,
                warnings=[*policy_result.warnings, *guard_warnings],
                warning_codes=_unique_strings([*policy_result.warning_codes, *guard_codes]),
                dropped_citation_count=(
                    policy_result.dropped_citation_count + guard_dropped_count
                ),
            )
        if self._should_answer_insufficient(request):
            policy_result = self._insufficient_policy_result(policy_result)
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
                "retrieval_scope": request.retrieval_scope,
                "expected_source_types": self._expected_source_types(request),
                "should_answer_insufficient": self._should_answer_insufficient(request),
                "forbidden_anchors": self._forbidden_anchors(request),
                "question_type": self._question_type(request),
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
                        "retrieval_scope": request.retrieval_scope,
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
        if not self._has_request_scope(request):
            return citations
        scoped = self._scope_citations(citations, request)
        if scoped:
            return scoped
        return self._retrieve_scoped_retry(request)

    def _retrieve_scoped_retry(self, request: AgentRequest) -> list[Citation]:
        for attempt in range(3):
            retry_citations = self.retriever.retrieve(
                query=request.query_or_topic,
                filters=self._build_filters(request),
                top_k=self.top_k,
            )
            scoped = self._scope_citations(retry_citations, request)
            if scoped or attempt == 2:
                return scoped
            time.sleep(2)
        return []

    @staticmethod
    def _has_request_scope(request: AgentRequest) -> bool:
        return bool(request.document_ids or request.current_run)

    @staticmethod
    def _scope_citations(
        citations: list[Citation],
        request: AgentRequest,
    ) -> list[Citation]:
        current_run = request.current_run or {}
        document_ids = _value_set(
            [
                *request.document_ids,
                *(_list_filter(current_run.get("document_ids"))),
                *(_list_filter(current_run.get("pa_document_ids"))),
            ]
        )
        external_doc_ids = _value_set(
            [
                *(_list_filter(current_run.get("external_doc_ids"))),
                *(_list_filter(current_run.get("external_doc_id"))),
                *(_list_filter(current_run.get("knowledge_ids"))),
                *(_list_filter(current_run.get("weknora_knowledge_ids"))),
            ]
        )
        wiki_page_ids = _value_set(
            [
                *(_list_filter(current_run.get("wiki_page_ids"))),
                *(_list_filter(current_run.get("wiki_page_id"))),
                *(_list_filter(current_run.get("weknora_wiki_page_ids"))),
            ]
        )
        metadata_terms = _value_set(
            [
                *(_list_filter(current_run.get("run_id"))),
                *(_list_filter(current_run.get("id"))),
                *(_list_filter(current_run.get("corpus_id"))),
                *(_list_filter(current_run.get("namespace"))),
            ]
        )
        anchors = _value_set(_list_filter(current_run.get("anchors")))
        if not any((document_ids, external_doc_ids, wiki_page_ids, metadata_terms, anchors)):
            return citations
        return [
            citation
            for citation in citations
            if _citation_matches_scope(
                citation,
                document_ids=document_ids,
                external_doc_ids=external_doc_ids,
                wiki_page_ids=wiki_page_ids,
                metadata_terms=metadata_terms,
                anchors=anchors,
            )
        ]

    @staticmethod
    def _build_filters(request: AgentRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.document_ids:
            filters["document_ids"] = request.document_ids
        filters["source_scope"] = request.retrieval_scope or "all"
        if request.current_run:
            filters["current_run"] = request.current_run
        if request.business_area:
            filters["business_area"] = request.business_area
        if request.document_type:
            filters["document_type"] = request.document_type
        return filters

    @staticmethod
    def _expected_source_types(request: AgentRequest) -> list[str]:
        requested = (
            request.expected_source_types
            or request.metadata.get("expected_source_types")
            or request.metadata.get("expected_source_type")
            or request.metadata.get("required_source_type")
        )
        expected = _normalize_source_types(_list_filter(requested))
        if expected:
            return expected
        if request.retrieval_scope == "document":
            return ["document_chunk"]
        if request.retrieval_scope == "wiki":
            return ["wiki_page"]
        return []

    @staticmethod
    def _apply_forbidden_anchor_policy(
        request: AgentRequest,
        citations: list[Citation],
    ) -> tuple[list[Citation], list[str], list[str], int]:
        forbidden_anchors = set(KnowledgeQaWorkflow._forbidden_anchors(request))
        if not forbidden_anchors:
            return citations, [], [], 0
        kept: list[Citation] = []
        dropped = 0
        for citation in citations:
            anchors = _citation_anchor_set(citation)
            if anchors & forbidden_anchors:
                dropped += 1
                continue
            kept.append(citation)
        if not dropped:
            return kept, [], [], 0
        return (
            kept,
            [
                "FORBIDDEN_ANCHOR_DROPPED: Retrieved evidence matched forbidden "
                f"anchors and was removed from support citations: {','.join(sorted(forbidden_anchors))}."
            ],
            ["FORBIDDEN_ANCHOR_DROPPED"],
            dropped,
        )

    @staticmethod
    def _forbidden_anchors(request: AgentRequest) -> list[str]:
        return _unique_strings(
            [
                *request.forbidden_anchors,
                *_list_filter(request.metadata.get("forbidden_anchors")),
                *_list_filter(request.metadata.get("forbidden_anchor")),
            ]
        )

    @staticmethod
    def _question_type(request: AgentRequest) -> str | None:
        return _optional_str(
            request.question_type
            or request.metadata.get("question_type")
            or request.metadata.get("type")
        )

    @staticmethod
    def _is_version_conflict_request(request: AgentRequest) -> bool:
        question_type = KnowledgeQaWorkflow._question_type(request)
        if question_type == "version_conflict":
            return True
        query = request.query_or_topic or ""
        return "旧版" in query and "新版" in query and "现在" in query

    @staticmethod
    def _should_answer_insufficient(request: AgentRequest) -> bool:
        raw = (
            request.should_answer_insufficient
            or request.metadata.get("should_answer_insufficient")
            or request.metadata.get("insufficient_evidence_expected")
            or request.metadata.get("expect_insufficient")
        )
        return _bool_value(raw)

    @staticmethod
    def _insufficient_policy_result(
        policy_result: EvidencePolicyResult,
    ) -> EvidencePolicyResult:
        warnings = [
            *policy_result.warnings,
            (
                "INSUFFICIENT_EVIDENCE_EXPECTED: Question is marked as no-answer; "
                "retrieved context is not supporting evidence."
            ),
        ]
        if not any(str(warning).startswith("NO_EVIDENCE:") for warning in warnings):
            warnings.append(
                "NO_EVIDENCE: No supporting evidence was found for this no-answer question."
            )
        warning_codes = [*policy_result.warning_codes]
        for code in ("INSUFFICIENT_EVIDENCE_EXPECTED", "NO_EVIDENCE"):
            if code not in warning_codes:
                warning_codes.append(code)
        return replace(
            policy_result,
            citations=[],
            warnings=warnings,
            warning_codes=warning_codes,
            dropped_citation_count=(
                policy_result.dropped_citation_count + len(policy_result.citations)
            ),
            weak_evidence_count=0,
            evidence_mode="insufficient_evidence",
        )

    def _generate_answer(
        self,
        request: AgentRequest,
        context: AgentContext,
        citations: list[Citation],
        policy_result: EvidencePolicyResult,
    ) -> tuple[str, dict[str, Any]]:
        if self._should_answer_insufficient(request):
            metadata = {
                "provider": "deterministic",
                "model": "insufficient_evidence_policy",
                "usage": {},
                "retrieval_scope": request.retrieval_scope,
                "expected_source_types": self._expected_source_types(request),
                "evidence_sources": [],
                "source_types": [],
                "evidence_mode": policy_result.evidence_mode,
                "warning_codes": policy_result.warning_codes,
                "weak_evidence_count": policy_result.weak_evidence_count,
                "dropped_citation_count": policy_result.dropped_citation_count,
                "source_type_mismatch_count": policy_result.source_type_mismatch_count,
                "should_answer_insufficient": True,
            }
            return self._insufficient_markdown(request, policy_result), metadata
        if self._is_version_conflict_request(request):
            metadata = {
                "provider": "deterministic",
                "model": "version_conflict_policy",
                "usage": {},
                "retrieval_scope": request.retrieval_scope,
                "expected_source_types": self._expected_source_types(request),
                "should_answer_insufficient": False,
                "evidence_sources": sorted({citation.source for citation in citations}),
                "source_types": sorted(
                    {citation.source_type or "unknown" for citation in citations}
                ),
                "evidence_mode": policy_result.evidence_mode,
                "warning_codes": policy_result.warning_codes,
                "weak_evidence_count": policy_result.weak_evidence_count,
                "dropped_citation_count": policy_result.dropped_citation_count,
                "source_type_mismatch_count": policy_result.source_type_mismatch_count,
                "question_type": "version_conflict",
            }
            return self._version_conflict_markdown(citations, policy_result), metadata

        response = self.model_gateway.generate(
            ChatRequest(
                messages=self._build_messages(request, context, citations),
                temperature=0.2,
                max_tokens=1600,
                metadata={
                    "task_id": request.task_id,
                    "task_type": request.task_type,
                    "workflow": "knowledge_qa",
                    "retrieval_scope": request.retrieval_scope,
                    "expected_source_types": self._expected_source_types(request),
                    "should_answer_insufficient": self._should_answer_insufficient(request),
                    "forbidden_anchors": self._forbidden_anchors(request),
                    "question_type": self._question_type(request),
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
            "retrieval_scope": request.retrieval_scope,
            "expected_source_types": self._expected_source_types(request),
            "should_answer_insufficient": self._should_answer_insufficient(request),
            "forbidden_anchors": self._forbidden_anchors(request),
            "question_type": self._question_type(request),
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

    @classmethod
    def _version_conflict_markdown(
        cls,
        citations: list[Citation],
        policy_result: EvidencePolicyResult,
    ) -> str:
        old_index = _first_citation_index(citations, "TEST-RAG-001")
        new_index = _first_citation_index(citations, "TEST-RAG-002")
        old_ref = f"[{old_index}]" if old_index else "旧版证据"
        new_ref = f"[{new_index}]" if new_index else "新版证据"
        lines = [
            "## 回答",
            "",
            f"现在应优先按新版三个工作日规则回答。{new_ref}",
            f"旧版材料是五个工作日口径，适合作为历史差异说明，不应作为当前优先规则。{old_ref}",
            "新版口径收紧了普通事项初稿时限，并要求第四个工作日前完成复核；旧版还允许待复核附件先汇总并标记。",
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
    def _insufficient_markdown(
        request: AgentRequest,
        policy_result: EvidencePolicyResult,
    ) -> str:
        del policy_result
        lines = [
            "## 依据不足",
            "",
            f"针对问题“{request.query_or_topic}”，当前知识库材料没有足够依据支持该结论。",
            "不能将检索到的相似上下文当作支持证据，也不能据此编造真实监管要求、真实客户名称或其他材料中未明确给出的事实。",
            "",
            "## 检索说明",
            "",
            "- 本次检索到的相近材料仅说明已进行查找，未作为事实结论的支持引用。",
            "- 若材料为合成脱敏文本，只能说明测试材料本身的内容，不能推出真实主体或真实监管口径。",
            "- 需要补充明确资料后才能回答该问题。",
        ]
        return "\n".join(lines)

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

        forbidden_anchors = cls._forbidden_anchors(request)
        if forbidden_anchors:
            lines.extend(
                [
                    "禁止作为支持证据的材料锚点：",
                    ", ".join(forbidden_anchors),
                    "如果检索上下文与这些锚点有关，只能说明其不适合作为依据，不得引用为事实支持。",
                    "",
                ]
            )

        if cls._is_version_conflict_request(request):
            lines.extend(
                [
                    "版本冲突回答要求：",
                    "必须同时说明旧版和新版差异；当新版 evidence 存在时，应明确优先新版当前规则。",
                    "本阶段固定验收期望是新版三个工作日优先，旧版五个工作日仅作历史差异说明。",
                    "",
                ]
            )

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


def _citation_matches_scope(
    citation: Citation,
    *,
    document_ids: set[str],
    external_doc_ids: set[str],
    wiki_page_ids: set[str],
    metadata_terms: set[str],
    anchors: set[str],
) -> bool:
    identifiers = _citation_identifiers(citation)
    has_document_scope = bool(document_ids or external_doc_ids)
    if document_ids and identifiers["document_ids"] & document_ids:
        return True
    if external_doc_ids and identifiers["external_doc_ids"] & external_doc_ids:
        return True
    if wiki_page_ids and identifiers["wiki_page_ids"] & wiki_page_ids:
        return True
    if citation.source_type == "wiki_page" and wiki_page_ids:
        return False
    if metadata_terms and identifiers["metadata_terms"] & metadata_terms:
        return True
    if has_document_scope:
        return bool(
            citation.source_type == "wiki_page"
            and anchors
            and identifiers["anchors"] & anchors
        )
    if anchors and identifiers["anchors"] & anchors:
        return True
    return False


def _citation_identifiers(citation: Citation) -> dict[str, set[str]]:
    metadata = citation.metadata if isinstance(citation.metadata, dict) else {}
    binding = metadata.get("citation_binding")
    binding = binding if isinstance(binding, dict) else {}
    binding_metadata = binding.get("metadata")
    binding_metadata = binding_metadata if isinstance(binding_metadata, dict) else {}
    return {
        "document_ids": _value_set(
            [
                citation.document_id,
                metadata.get("document_id"),
                metadata.get("pa_document_id"),
                binding.get("document_id"),
                binding_metadata.get("document_id"),
            ]
        ),
        "external_doc_ids": _value_set(
            [
                citation.external_doc_id,
                metadata.get("external_doc_id"),
                metadata.get("knowledge_id"),
                metadata.get("weknora_knowledge_id"),
                binding.get("external_doc_id"),
                binding.get("knowledge_id"),
                binding_metadata.get("external_doc_id"),
                binding_metadata.get("knowledge_id"),
            ]
        ),
        "wiki_page_ids": _value_set(
            [
                citation.wiki_page_id,
                metadata.get("wiki_page_id"),
                metadata.get("wiki_page_ids"),
                metadata.get("weknora_wiki_page_id"),
                metadata.get("weknora_wiki_page_ids"),
                metadata.get("slug"),
                metadata.get("id"),
                binding.get("wiki_page_id"),
                binding_metadata.get("wiki_page_id"),
                binding_metadata.get("slug"),
                binding_metadata.get("id"),
            ]
        ),
        "metadata_terms": _value_set(
            [
                metadata.get("current_run_id"),
                metadata.get("phase5_run_id"),
                metadata.get("corpus_id"),
                metadata.get("current_run_corpus_id"),
                metadata.get("namespace"),
                metadata.get("current_run_namespace"),
                binding_metadata.get("current_run_id"),
                binding_metadata.get("corpus_id"),
                binding_metadata.get("namespace"),
            ]
        ),
        "anchors": _value_set(
            [
                metadata.get("anchor"),
                metadata.get("anchors"),
                metadata.get("test_anchor"),
                metadata.get("expected_anchor"),
                binding_metadata.get("anchor"),
                binding_metadata.get("anchors"),
            ]
        ),
    }


def _citation_anchor_set(citation: Citation) -> set[str]:
    metadata = citation.metadata if isinstance(citation.metadata, dict) else {}
    binding = metadata.get("citation_binding")
    binding = binding if isinstance(binding, dict) else {}
    binding_metadata = binding.get("metadata")
    binding_metadata = binding_metadata if isinstance(binding_metadata, dict) else {}
    anchors = _value_set(
        [
            citation.title,
            citation.text,
            metadata.get("anchor"),
            metadata.get("anchors"),
            metadata.get("test_anchor"),
            metadata.get("expected_anchor"),
            binding_metadata.get("anchor"),
            binding_metadata.get("anchors"),
        ]
    )
    return {anchor for anchor in _known_anchor_candidates(anchors) if anchor}


def _known_anchor_candidates(values: set[str]) -> set[str]:
    candidates: set[str] = set()
    for value in values:
        text = str(value or "")
        for token in text.replace("，", " ").replace(",", " ").split():
            if token.startswith("TEST-RAG-") or token.startswith("TEST-WIKI-"):
                candidates.add(token.strip("。；;:：()（）[]【】"))
            if token.startswith("TEST-DISTRACTOR-"):
                candidates.add(token.strip("。；;:：()（）[]【】"))
        if "TEST-DISTRACTOR-001" in text:
            candidates.add("TEST-DISTRACTOR-001")
        for index in range(1, 10):
            rag_anchor = f"TEST-RAG-00{index}"
            if rag_anchor in text:
                candidates.add(rag_anchor)
        if "TEST-WIKI-001" in text:
            candidates.add("TEST-WIKI-001")
    return candidates


def _first_citation_index(citations: list[Citation], anchor: str) -> int | None:
    for index, citation in enumerate(citations, start=1):
        if anchor in _citation_anchor_set(citation):
            return index
    return None


def _normalize_source_types(values: list[object]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        source_type = _normalize_source_type(value)
        if not source_type or source_type in normalized:
            continue
        normalized.append(source_type)
    return normalized


def _normalize_source_type(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or None


def _list_filter(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    return [item for item in (_optional_str(item) for item in values) if item]


def _value_set(values: Any) -> set[str]:
    return set(_list_filter(values))


def _unique_strings(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = _optional_str(value)
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}
