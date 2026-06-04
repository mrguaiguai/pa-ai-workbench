import json
import re
from typing import Any

from sqlmodel import Session
from sqlmodel import select

from app import pathing as _pathing  # noqa: F401
from app.models import Citation
from app.models import GeneratedOutput
from app.models import utc_now
from app.models import WikiCitation
from app.models import WikiPage as WikiPageModel
from app.schemas import WikiDraftFromOutputRequest
from app.schemas import WikiCitationPayload
from app.schemas import WikiPageCreateRequest
from app.schemas import WikiPageUpdateRequest
from agent.model_gateway import ChatMessage
from agent.model_gateway import ChatMessageRole
from agent.model_gateway import ChatRequest
from agent.model_gateway import get_model_gateway
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary
from knowledge_engine.wiki import WikiPageStatus


class WikiPageConflictError(Exception):
    pass


class WikiPageNotFoundError(Exception):
    pass


class WikiDraftSourceNotFoundError(Exception):
    pass


def search_wiki_page_records(
    session: Session,
    query: str = "",
    limit: int = 10,
) -> list[WikiPageModel]:
    statement = select(WikiPageModel).order_by(WikiPageModel.updated_at.desc())
    pages = list(session.exec(statement).all())
    normalized_query = query.strip().lower()
    if normalized_query:
        pages = [
            page
            for page in pages
            if normalized_query in page.slug.lower()
            or normalized_query in page.title.lower()
            or normalized_query in (page.summary or "").lower()
            or normalized_query in page.content_markdown.lower()
        ]
    return pages[:limit]


def get_wiki_page_record(session: Session, slug: str) -> WikiPageModel | None:
    statement = select(WikiPageModel).where(WikiPageModel.slug == slug)
    return session.exec(statement).first()


def list_wiki_citation_records(
    session: Session,
    wiki_page_id: str,
) -> list[WikiCitation]:
    statement = (
        select(WikiCitation)
        .where(WikiCitation.wiki_page_id == wiki_page_id)
        .order_by(WikiCitation.created_at)
    )
    return list(session.exec(statement).all())


def create_wiki_page_record(
    session: Session,
    payload: WikiPageCreateRequest,
) -> WikiPageModel:
    slug = _normalize_slug(payload.slug)
    if get_wiki_page_record(session, slug) is not None:
        raise WikiPageConflictError(f"Wiki page already exists: {slug}")

    page = WikiPageModel(
        slug=slug,
        title=_normalize_title(payload.title),
        summary=payload.summary,
        content_markdown=payload.content_markdown,
        tags_json=_to_json(payload.tags),
        business_area=payload.business_area,
        page_type=payload.page_type,
        source_output_id=payload.source_output_id,
        source_document_ids_json=_to_json(payload.source_document_ids),
        source_citation_ids_json=_to_json(payload.source_citation_ids),
        created_by=payload.created_by,
        metadata_json=_to_json(payload.metadata),
    )
    session.add(page)
    session.flush()
    _replace_wiki_citations(session, page.id, payload.citations)
    session.commit()
    session.refresh(page)
    return page


def create_wiki_draft_from_output(
    session: Session,
    output_id: str,
    payload: WikiDraftFromOutputRequest | None = None,
) -> WikiPageModel:
    output = session.get(GeneratedOutput, output_id)
    if output is None:
        raise WikiDraftSourceNotFoundError(f"Output not found: {output_id}")

    payload = payload or WikiDraftFromOutputRequest()
    citations = list_output_citations_for_wiki(session=session, output_id=output_id)
    draft = _build_draft_from_output(output=output, citations=citations, payload=payload)
    draft.slug = _unique_slug(session=session, slug=draft.slug)
    return create_wiki_page_record(session=session, payload=draft)


def update_wiki_page_record(
    session: Session,
    slug: str,
    payload: WikiPageUpdateRequest,
) -> WikiPageModel:
    page = get_wiki_page_record(session, slug)
    if page is None:
        raise WikiPageNotFoundError(f"Wiki page not found: {slug}")

    updates = payload.model_dump(exclude_unset=True)
    for field_name in (
        "title",
        "summary",
        "content_markdown",
        "business_area",
        "page_type",
        "source_output_id",
        "created_by",
    ):
        if field_name in updates:
            value = updates[field_name]
            if field_name == "title" and isinstance(value, str):
                value = _normalize_title(value)
            setattr(page, field_name, value)

    if "tags" in updates:
        page.tags_json = _to_json(updates["tags"] or [])
    if "source_document_ids" in updates:
        page.source_document_ids_json = _to_json(updates["source_document_ids"] or [])
    if "source_citation_ids" in updates:
        page.source_citation_ids_json = _to_json(updates["source_citation_ids"] or [])
    if "metadata" in updates:
        page.metadata_json = _to_json(updates["metadata"] or {})
    if "citations" in updates:
        _replace_wiki_citations(session, page.id, payload.citations or [])

    page.updated_at = utc_now()
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


def publish_wiki_page_record(session: Session, slug: str) -> WikiPageModel:
    page = get_wiki_page_record(session, slug)
    if page is None:
        raise WikiPageNotFoundError(f"Wiki page not found: {slug}")

    if page.status == WikiPageStatus.PUBLISHED:
        return page

    now = utc_now()
    page.status = WikiPageStatus.PUBLISHED
    page.published_at = page.published_at or now
    page.updated_at = now
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


def list_output_citations_for_wiki(
    session: Session,
    output_id: str,
) -> list[Citation]:
    statement = (
        select(Citation)
        .where(Citation.output_id == output_id)
        .order_by(Citation.created_at)
    )
    return list(session.exec(statement).all())


def search_wiki_pages(
    query: str,
    kb_id: str | None = None,
    limit: int = 10,
) -> list[WikiPageSummary]:
    engine = create_knowledge_engine()
    return engine.search_wiki(query=query, kb_id=kb_id, limit=limit)


def read_wiki_page(slug: str, kb_id: str | None = None) -> WikiPage | None:
    engine = create_knowledge_engine()
    return engine.read_wiki_page(slug=slug, kb_id=kb_id)


def page_tags(page: WikiPageModel) -> list[str]:
    value = _from_json(page.tags_json, default=[])
    return value if isinstance(value, list) else []


def page_source_document_ids(page: WikiPageModel) -> list[str]:
    value = _from_json(page.source_document_ids_json, default=[])
    return value if isinstance(value, list) else []


def page_source_citation_ids(page: WikiPageModel) -> list[str]:
    value = _from_json(page.source_citation_ids_json, default=[])
    return value if isinstance(value, list) else []


def page_metadata(page: WikiPageModel) -> dict[str, Any]:
    value = _from_json(page.metadata_json, default={})
    return value if isinstance(value, dict) else {}


def citation_metadata(citation: WikiCitation) -> dict[str, Any]:
    value = _from_json(citation.metadata_json, default={})
    return value if isinstance(value, dict) else {}


def _build_draft_from_output(
    output: GeneratedOutput,
    citations: list[Citation],
    payload: WikiDraftFromOutputRequest,
) -> WikiPageCreateRequest:
    source_markdown = _output_markdown(output)
    model_draft = _generate_draft_with_model_gateway(output=output, citations=citations)
    title = _normalize_title(
        payload.title or _optional_str(model_draft.get("title")) or output.title
    )
    content_markdown = _optional_str(model_draft.get("content_markdown")) or source_markdown
    summary = payload.summary or _optional_str(model_draft.get("summary")) or _summarize_markdown(
        content_markdown
    )
    tags = payload.tags if payload.tags is not None else _normalize_tags(model_draft.get("tags"))
    if not tags:
        tags = _default_tags(output)

    metadata = {
        **(payload.metadata or {}),
        "source": "generated_output",
        "source_output_id": output.id,
        "source_task_id": output.task_id,
        "source_task_type": output.task_type,
        "draft_generator": model_draft.get("draft_generator", "fallback"),
    }
    if model_draft.get("model_provider"):
        metadata["model_provider"] = model_draft["model_provider"]
    if model_draft.get("model"):
        metadata["model"] = model_draft["model"]
    if model_draft.get("model_error"):
        metadata["model_error"] = model_draft["model_error"]

    return WikiPageCreateRequest(
        slug=_unique_slug_base(payload.slug or model_draft.get("slug") or title, output.id),
        title=title,
        summary=summary,
        content_markdown=content_markdown,
        tags=tags,
        business_area=payload.business_area,
        page_type=payload.page_type or output.task_type,
        source_output_id=output.id,
        source_document_ids=_source_document_ids(citations),
        source_citation_ids=[citation.id for citation in citations],
        created_by=payload.created_by,
        metadata=metadata,
        citations=[_output_citation_to_wiki_payload(citation) for citation in citations],
    )


def _replace_wiki_citations(
    session: Session,
    wiki_page_id: str,
    citations: list[WikiCitationPayload],
) -> None:
    for existing in list_wiki_citation_records(session, wiki_page_id):
        session.delete(existing)
    session.flush()
    for payload in citations:
        session.add(_citation_payload_to_model(wiki_page_id, payload))


def _citation_payload_to_model(
    wiki_page_id: str,
    payload: WikiCitationPayload,
) -> WikiCitation:
    return WikiCitation(
        wiki_page_id=wiki_page_id,
        document_id=payload.document_id,
        external_doc_id=payload.external_doc_id,
        chunk_id=payload.chunk_id,
        output_id=payload.output_id,
        citation_id=payload.citation_id,
        evidence_id=payload.evidence_id,
        source_type=payload.source_type,
        excerpt=payload.excerpt,
        score=payload.score,
        metadata_json=_to_json(payload.metadata),
    )


def _output_citation_to_wiki_payload(citation: Citation) -> WikiCitationPayload:
    metadata = _from_json(citation.metadata_json, default={})
    metadata = metadata if isinstance(metadata, dict) else {}
    binding = metadata.get("citation_binding")
    binding = binding if isinstance(binding, dict) else {}
    evidence_id = binding.get("evidence_id") or metadata.get("evidence_id")
    source_type = _normalize_source_type(
        binding.get("source_type")
        or metadata.get("citation_source_type")
        or metadata.get("source_type")
        or ("document_chunk" if citation.chunk_id else "document_chunk")
    )
    return WikiCitationPayload(
        document_id=citation.document_id,
        external_doc_id=citation.external_doc_id,
        chunk_id=citation.chunk_id,
        output_id=citation.output_id,
        citation_id=citation.id,
        evidence_id=_optional_str(evidence_id),
        source_type=source_type,
        excerpt=citation.text,
        score=citation.score,
        metadata={
            **metadata,
            "citation_title": citation.title,
            "citation_source": citation.source,
        },
    )


def _generate_draft_with_model_gateway(
    output: GeneratedOutput,
    citations: list[Citation],
) -> dict[str, object]:
    prompt = _draft_prompt(output=output, citations=citations)
    try:
        response = get_model_gateway().generate(
            ChatRequest(
                messages=[
                    ChatMessage(
                        role=ChatMessageRole.SYSTEM,
                        content=(
                            "You convert analysis outputs into concise Wiki drafts. "
                            "Return strict JSON only."
                        ),
                    ),
                    ChatMessage(role=ChatMessageRole.USER, content=prompt),
                ],
                temperature=0.2,
                max_tokens=1200,
                metadata={"task": "wiki_draft_from_output", "output_id": output.id},
            )
        )
        parsed = _parse_model_draft_json(response.content)
        if parsed:
            parsed["draft_generator"] = "model_gateway"
            parsed["model_provider"] = response.provider
            parsed["model"] = response.model
            return parsed
    except Exception as exc:
        return {
            "draft_generator": "fallback",
            "model_error": exc.__class__.__name__,
        }
    return {"draft_generator": "fallback"}


def _draft_prompt(output: GeneratedOutput, citations: list[Citation]) -> str:
    citation_lines = [
        {
            "id": citation.id,
            "title": citation.title,
            "excerpt": _excerpt(citation.text, 360),
        }
        for citation in citations[:12]
    ]
    payload = {
        "output_id": output.id,
        "title": output.title,
        "task_type": output.task_type,
        "content_markdown": _excerpt(_output_markdown(output), 5000),
        "citations": citation_lines,
        "required_json_shape": {
            "title": "string",
            "summary": "string",
            "content_markdown": "markdown string",
            "tags": ["short tag strings"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _parse_model_draft_json(content: str) -> dict[str, object]:
    text = content.strip()
    if not text:
        return {}
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _output_markdown(output: GeneratedOutput) -> str:
    if output.content_markdown and output.content_markdown.strip():
        return output.content_markdown.strip()
    if output.content_json and output.content_json.strip():
        try:
            value = json.loads(output.content_json)
        except json.JSONDecodeError:
            return output.content_json.strip()
        return _markdown_from_json_value(value)
    raise ValueError("Output has no content to convert into a Wiki draft.")


def _markdown_from_json_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            lines.append(f"## {key}")
            lines.append("")
            lines.append(_markdown_from_json_value(item))
            lines.append("")
        return "\n".join(line for line in lines if line is not None).strip()
    if isinstance(value, list):
        return "\n".join(f"- {_markdown_from_json_value(item)}" for item in value).strip()
    return str(value).strip()


def _summarize_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        normalized = line.strip().lstrip("#").strip()
        if normalized:
            return _excerpt(normalized, 180)
    return "由分析结果生成的 Wiki 草稿。"


def _normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    tags = []
    for item in value:
        tag = str(item).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:8]


def _default_tags(output: GeneratedOutput) -> list[str]:
    tags = ["generated-output"]
    if output.task_type:
        tags.append(output.task_type)
    return tags


def _source_document_ids(citations: list[Citation]) -> list[str]:
    document_ids = []
    for citation in citations:
        for value in (citation.document_id, citation.external_doc_id):
            if value and value not in document_ids:
                document_ids.append(value)
    return document_ids


def _unique_slug_base(value: object, output_id: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    if not normalized:
        normalized = f"wiki-output-{output_id.replace('_', '-')}"
    suffix = output_id.replace("_", "-")
    if suffix and not normalized.endswith(suffix):
        normalized = f"{normalized}-{suffix}"
    return normalized[:120].strip("-") or f"wiki-output-{suffix}"


def _unique_slug(session: Session, slug: str) -> str:
    base = slug
    candidate = base
    index = 2
    while get_wiki_page_record(session, candidate) is not None:
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def _normalize_source_type(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return "document_chunk"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _excerpt(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}[truncated]"


def _normalize_slug(slug: str) -> str:
    normalized = slug.strip()
    if not normalized:
        raise ValueError("Wiki page slug must not be empty.")
    return normalized


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise ValueError("Wiki page title must not be empty.")
    return normalized


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _from_json(value: str | None, default: object) -> object:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
