"""Fixture smoke for P5-C2 Wiki-only natural-language recall.

The fixture backend intentionally returns no result for the raw official
questions, then returns TEST-WIKI-001 only for PA's Wiki query variants. This
protects the adapter behavior without counting as real WeKnora PASS.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402


QUESTIONS_PATH = PROJECT_ROOT / "backend" / "fixtures" / "phase4_rag_wiki_qa" / "questions.json"
WIKI_IDS = {"P4Q-017", "P4Q-018", "P4Q-019"}


class SmokeError(RuntimeError):
    """Raised when Wiki natural-language recall expectations fail."""


class FixtureWikiBackend(WeKnoraApiBackend):
    def __init__(self, raw_queries: set[str]) -> None:
        super().__init__(
            base_url="http://weknora.fixture",
            service_token="fixture-token",
            default_kb_id="kb-fixture",
        )
        self.raw_queries = raw_queries
        self.search_calls: list[dict[str, Any]] = []

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        raise NotImplementedError

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        self.search_calls.append({"query": query, "kb_id": kb_id, "limit": limit})
        if query in self.raw_queries:
            return []
        if _query_matches_fixture_wiki(query):
            return [
                WikiPageSummary(
                    slug="phase5/p5-c2-timeliness",
                    title="TEST-WIKI-001 时限管理专题 Wiki",
                    page_type="wiki",
                    summary="时限管理专题关联政策、法规、案例，并列出常见误区。",
                    source="weknora_api",
                    metadata={
                        "id": "wiki-p5-c2",
                        "anchor": "TEST-WIKI-001",
                        "anchors": ["TEST-WIKI-001"],
                    },
                )
            ]
        return []

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        if slug != "phase5/p5-c2-timeliness":
            return None
        return WikiPage(
            slug=slug,
            title="TEST-WIKI-001 时限管理专题 Wiki",
            page_type="wiki",
            summary="时限管理专题关联政策、法规、案例，并列出常见误区。",
            content=(
                "TEST-WIKI-001\n"
                "时限管理专题关联旧版和新版专项信息报送政策、数据留存与访问审计规则、"
                "外部材料引用与发布校验规则、蓝湾和北辰案例。\n"
                "常见误区包括只看最终提交日期、误以为 Wiki 发布等于立即可检索、"
                "以及用相似材料推断无答案问题。\n"
                "发布后的 Wiki evidence 应带有 source_type=wiki_page，并与原始文档 evidence 区分。"
            ),
            citations=[],
            source="weknora_api",
            metadata={
                "id": "wiki-p5-c2",
                "status": "published",
                "anchor": "TEST-WIKI-001",
                "anchors": ["TEST-WIKI-001"],
            },
        )


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 Wiki natural recall smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Phase 5 Wiki natural recall smoke passed (fixture)")
    print("- scope: fixture contract only; this is not real WeKnora PASS")
    print(f"- questions: {', '.join(result['question_ids'])}")
    print(f"- fallback calls: {result['fallback_calls']}")
    print(f"- evidence id: {result['evidence_id']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    questions = _wiki_questions()
    backend = FixtureWikiBackend(raw_queries={str(question["query"]) for question in questions})
    evidence_id = ""
    fallback_calls = 0

    for question in questions:
        evidence = _retrieve_one(backend=backend, question=question)
        evidence_id = evidence.evidence_id or evidence_id
        if evidence.metadata.get("wiki_search_query") == question["query"]:
            raise SmokeError(f"{question['id']} did not use a natural-language fallback query")
        if evidence.source != "weknora_api":
            raise SmokeError(f"{question['id']} source mismatch: {evidence.source}")
        if evidence.source_type != "wiki_page":
            raise SmokeError(f"{question['id']} source_type mismatch: {evidence.source_type}")
        if evidence.wiki_page_id != "wiki-p5-c2":
            raise SmokeError(f"{question['id']} wiki_page_id mismatch: {evidence.wiki_page_id}")
        if "TEST-WIKI-001" not in _evidence_text(evidence):
            raise SmokeError(f"{question['id']} missing TEST-WIKI-001 anchor")
        fallback_calls += sum(
            1
            for call in backend.search_calls
            if call["query"] != question["query"] and _query_matches_fixture_wiki(call["query"])
        )

    if fallback_calls < len(questions):
        raise SmokeError(f"expected fallback search calls for all wiki questions, got {fallback_calls}")
    return {
        "question_ids": [str(question["id"]) for question in questions],
        "fallback_calls": fallback_calls,
        "evidence_id": evidence_id,
    }


def _retrieve_one(backend: FixtureWikiBackend, question: dict[str, Any]) -> Evidence:
    items = backend.retrieve(
        query=str(question["query"]),
        filters={"source_type": "wiki_page", "knowledge_base_ids": ["kb-fixture"]},
        top_k=3,
    )
    if not items:
        raise SmokeError(f"{question['id']} returned no wiki evidence")
    return items[0]


def _wiki_questions() -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = [
        question
        for question in payload["questions"]
        if str(question.get("id")) in WIKI_IDS
    ]
    if {str(question["id"]) for question in questions} != WIKI_IDS:
        raise SmokeError("missing official Wiki-only fixture questions")
    return sorted(questions, key=lambda question: str(question["id"]))


def _query_matches_fixture_wiki(query: str) -> bool:
    return any(
        marker in query
        for marker in (
            "关联政策",
            "政策 法规 案例",
            "常见误区",
            "source_type=wiki_page",
            "原始文档 evidence 区分",
        )
    )


def _evidence_text(evidence: Evidence) -> str:
    metadata_values = " ".join(str(value) for value in evidence.metadata.values())
    return " ".join([evidence.title, evidence.text, metadata_values])


if __name__ == "__main__":
    raise SystemExit(main())
