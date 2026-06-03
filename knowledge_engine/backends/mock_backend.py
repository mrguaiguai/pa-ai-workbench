from pathlib import Path
from uuid import uuid4

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary


class MockKnowledgeBackend(KnowledgeEngine):
    def __init__(self) -> None:
        self._documents: dict[str, KnowledgeDocument] = {}
        self._evidence = [
            Evidence(
                document_id="mock_doc_policy_001",
                external_doc_id="mock_ext_policy_001",
                chunk_id="mock_chunk_policy_001",
                title="Mock 监管政策摘要",
                text="本 mock 资料用于演示政策背景、核心要求、影响评估与风险提示。",
                score=0.92,
                source="mock",
                metadata={"business_area": "securities", "document_type": "policy"},
            ),
            Evidence(
                document_id="mock_doc_case_001",
                external_doc_id="mock_ext_case_001",
                chunk_id="mock_chunk_case_001",
                title="Mock 历史案例复盘",
                text="本 mock 案例包含背景、时间线、沟通动作和经验教训。",
                score=0.87,
                source="mock",
                metadata={"business_area": "public_affairs", "document_type": "case"},
            ),
        ]
        self._wiki_pages = {
            "mock-policy-watch": WikiPage(
                slug="mock-policy-watch",
                title="Mock 政策观察",
                page_type="policy",
                summary="用于演示 Wiki 搜索和阅读的 mock 政策页面。",
                content="## Mock 政策观察\n\n本页面用于验证 Wiki read fallback。",
                citations=[self._evidence[0]],
                source="mock",
                metadata={"kb_id": "mock"},
            ),
            "mock-case-playbook": WikiPage(
                slug="mock-case-playbook",
                title="Mock 案例打法",
                page_type="case",
                summary="用于演示历史案例沉淀的 mock Wiki 页面。",
                content="## Mock 案例打法\n\n本页面用于验证案例复盘 fallback。",
                citations=[self._evidence[1]],
                source="mock",
                metadata={"kb_id": "mock"},
            ),
        }

    def health(self) -> dict:
        return {
            "status": "ok",
            "backend": "mock",
            "source": "mock",
            "documents": len(self._documents),
            "evidence": len(self._evidence),
            "wiki_pages": len(self._wiki_pages),
        }

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        path = Path(file_path)
        external_doc_id = f"mock_ext_{uuid4().hex[:12]}"
        document = KnowledgeDocument(
            document_id=metadata.get("document_id"),
            external_doc_id=external_doc_id,
            title=metadata.get("title") or path.name,
            status="indexed",
            source="mock",
            metadata={**metadata, "file_path": str(path)},
        )
        self._documents[external_doc_id] = document
        return document

    def get_document_status(self, external_doc_id: str) -> dict:
        document = self._documents.get(external_doc_id)
        if document is None:
            return {
                "external_doc_id": external_doc_id,
                "status": "not_found",
                "source": "mock",
            }
        return {
            "external_doc_id": external_doc_id,
            "status": document.status,
            "source": "mock",
        }

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        normalized_query = query.strip().lower()
        filtered = [
            evidence
            for evidence in self._evidence
            if self._matches_filters(evidence.metadata, filters)
        ]
        if normalized_query:
            ranked = sorted(
                filtered,
                key=lambda evidence: self._score_query_match(evidence, normalized_query),
                reverse=True,
            )
        else:
            ranked = filtered
        return ranked[:top_k]

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        normalized_query = query.strip().lower()
        pages = [
            page
            for page in self._wiki_pages.values()
            if kb_id is None or page.metadata.get("kb_id") == kb_id
        ]
        if normalized_query:
            pages = [
                page
                for page in pages
                if normalized_query in page.title.lower()
                or normalized_query in page.summary.lower()
                or normalized_query in page.content.lower()
            ]
        return [
            WikiPageSummary(
                slug=page.slug,
                title=page.title,
                page_type=page.page_type,
                summary=page.summary,
                source="mock",
                metadata=page.metadata,
            )
            for page in pages[:limit]
        ]

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        page = self._wiki_pages.get(slug)
        if page is None:
            return None
        if kb_id is not None and page.metadata.get("kb_id") != kb_id:
            return None
        return page

    @staticmethod
    def _matches_filters(metadata: dict, filters: dict | None) -> bool:
        if not filters:
            return True
        return all(metadata.get(key) == value for key, value in filters.items())

    @staticmethod
    def _score_query_match(evidence: Evidence, normalized_query: str) -> int:
        haystack = f"{evidence.title} {evidence.text}".lower()
        return int(normalized_query in haystack)
