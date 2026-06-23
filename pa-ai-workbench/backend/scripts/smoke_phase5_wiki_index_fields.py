"""Fixture smoke for P5-C1 published Wiki index field coverage.

This checks PA-side Wiki payload construction only. It does not contact
WeKnora and is not real WeKnora PASS evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app.models import WikiCitation  # noqa: E402
from app.models import WikiPage as WikiPageModel  # noqa: E402
from app.services.wiki_service import _weknora_wiki_payload  # noqa: E402
from app.services.wiki_service import _wiki_embedding_text  # noqa: E402
from app.services.wiki_service import _wiki_vector_metadata  # noqa: E402
from knowledge_engine.embeddings.schemas import EmbeddingVector  # noqa: E402
from knowledge_engine.wiki import WikiPageStatus  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the P5-C1 Wiki index field contract is broken."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 Wiki index field smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Phase 5 Wiki index field smoke passed (fixture)")
    print("- scope: fixture contract only; this is not real WeKnora PASS")
    print(f"- slug: {result['slug']}")
    print(f"- aliases: {result['alias_count']}")
    print(f"- source refs: {result['source_ref_count']}")
    print(f"- chunk refs: {result['chunk_ref_count']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    with TemporaryDirectory(prefix="pa-phase5-wiki-index-fields-"):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            page = _fixture_page()
            session.add(page)
            session.commit()
            session.refresh(page)
            session.add(_fixture_citation(page.id))
            session.commit()

            metadata = json.loads(page.metadata_json or "{}")
            payload = _weknora_wiki_payload(session=session, page=page, metadata=metadata)
            _assert_payload(payload, page)
            _assert_vector_metadata(page)
            return {
                "slug": payload["slug"],
                "alias_count": len(payload["aliases"]),
                "source_ref_count": len(payload["source_refs"]),
                "chunk_ref_count": len(payload["chunk_refs"]),
            }


def _fixture_page() -> WikiPageModel:
    return WikiPageModel(
        slug="phase5/p5-c1-timeliness",
        title="TEST-WIKI-001 时限管理专题 Wiki",
        summary="时限管理专题关联政策、法规、案例，并说明 source_type=wiki_page evidence。",
        content_markdown=(
            "TEST-WIKI-001\n"
            "旧版和新版专项信息报送政策、数据留存与访问审计规则、外部材料发布校验、"
            "蓝湾和北辰案例都属于该专题。\n"
            "Wiki 常见误区包括只看最终提交日期、误以为发布立即可检索、以及用相似材料推断无答案问题。"
        ),
        status=WikiPageStatus.PUBLISHED,
        tags_json=json.dumps(["时限管理", "Wiki 检索", "Phase5"], ensure_ascii=False),
        business_area="phase5-fixture",
        page_type="wiki",
        source_output_id="out-p5-c1",
        source_document_ids_json=json.dumps(["pa-doc-wiki-seed"], ensure_ascii=False),
        source_citation_ids_json=json.dumps(["cite-p5-c1"], ensure_ascii=False),
        metadata_json=json.dumps(
            {
                "kb_id": "kb-p5-c1",
                "anchor": "TEST-WIKI-001",
                "anchors": ["TEST-WIKI-001"],
                "test_anchor": "TEST-WIKI-001",
                "current_run_id": "phase5-p5-c1",
                "source": "phase5_fixture",
            },
            ensure_ascii=False,
        ),
    )


def _fixture_citation(wiki_page_id: str) -> WikiCitation:
    return WikiCitation(
        wiki_page_id=wiki_page_id,
        document_id="pa-doc-wiki-seed",
        external_doc_id="wk-doc-wiki-seed",
        chunk_id="wk-chunk-wiki-seed",
        output_id="out-p5-c1",
        citation_id="cite-p5-c1",
        evidence_id="document_chunk:wk-chunk-wiki-seed",
        source_type="document_chunk",
        excerpt="TEST-WIKI-001 source seed excerpt.",
        score=0.91,
        metadata_json=json.dumps({"citation_title": "时限管理专题 Wiki 种子材料"}, ensure_ascii=False),
    )


def _assert_payload(payload: dict[str, Any], page: WikiPageModel) -> None:
    metadata = payload.get("page_metadata")
    _assert(isinstance(metadata, dict), "payload page_metadata must be a dict")
    content = str(payload.get("content") or "")
    aliases = payload.get("aliases")
    _assert(isinstance(aliases, list) and aliases, "payload aliases must be populated")

    for expected in (
        page.title,
        page.slug,
        "source_type=wiki_page",
        "TEST-WIKI-001",
        "关联政策、法规、案例",
        "发布立即可检索",
        "wk-doc-wiki-seed",
        "wk-chunk-wiki-seed",
    ):
        _assert(expected in content, f"published Wiki index content missing {expected}")

    for key, expected in {
        "source_type": "wiki_page",
        "citation_source_type": "wiki_page",
        "wiki_page_id": page.id,
        "pa_wiki_page_id": page.id,
        "pa_wiki_slug": page.slug,
        "pa_wiki_status": WikiPageStatus.PUBLISHED,
        "anchor": "TEST-WIKI-001",
        "test_anchor": "TEST-WIKI-001",
        "wiki_index_field_version": "p5-c1",
    }.items():
        _assert(metadata.get(key) == expected, f"metadata {key} mismatch: {metadata.get(key)!r}")

    _assert(metadata.get("anchors") == ["TEST-WIKI-001"], "metadata anchors missing")
    _assert(metadata.get("pa_tags") == ["时限管理", "Wiki 检索", "Phase5"], "metadata tags missing")
    _assert(metadata.get("pa_source_document_ids") == ["pa-doc-wiki-seed"], "source docs missing")
    _assert(metadata.get("pa_source_citation_ids") == ["cite-p5-c1"], "source citations missing")
    _assert(metadata.get("source_refs") == ["wk-doc-wiki-seed|时限管理专题 Wiki 种子材料"], "source refs missing")
    _assert(metadata.get("chunk_refs") == ["wk-chunk-wiki-seed"], "chunk refs missing")
    _assert("wiki_index_text" in metadata, "metadata wiki_index_text missing")
    _assert(payload["source_refs"] == metadata["source_refs"], "top-level source refs mismatch")
    _assert(payload["chunk_refs"] == metadata["chunk_refs"], "top-level chunk refs mismatch")
    _assert("source_type=wiki_page" in aliases, "aliases missing source_type marker")
    _assert("TEST-WIKI-001" in aliases, "aliases missing test anchor")


def _assert_vector_metadata(page: WikiPageModel) -> None:
    text = _wiki_embedding_text(page)
    vector_metadata = _wiki_vector_metadata(
        page=page,
        embedding=EmbeddingVector(
            text_hash="phase5-p5-c1-hash",
            vector=[0.1, 0.2, 0.3],
            dimension=3,
            provider="fixture",
            model="fixture-embedding",
        ),
    )
    _assert("TEST-WIKI-001" in text, "embedding text missing wiki anchor")
    _assert(vector_metadata["source_type"] == "wiki_page", "vector metadata source_type mismatch")
    _assert(vector_metadata["anchor"] == "TEST-WIKI-001", "vector metadata anchor missing")
    _assert(vector_metadata["anchors"] == ["TEST-WIKI-001"], "vector metadata anchors missing")
    _assert("source_type=wiki_page" in vector_metadata["aliases"], "vector aliases missing source_type marker")
    _assert(vector_metadata["wiki_metadata"]["pa_wiki_slug"] == page.slug, "vector wiki metadata slug missing")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
