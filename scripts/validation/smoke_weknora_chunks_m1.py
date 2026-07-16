"""Smoke-check WeKnora chunk preview mapping for PA documents.

This fixture smoke validates P3-M1-B5 without a live WeKnora service:
- PA document chunk listing uses WeKnora chunk IDs for weknora_api documents.
- WeKnora start/end offsets and excerpt text are exposed through DocumentChunkRead.
- Raw WeKnora fields stay inside PA metadata_json instead of leaking a raw shape.
"""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.models import Document  # noqa: E402
from app.schemas import DocumentChunkRead  # noqa: E402
from app.services import document_service  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the chunk preview contract fails."""


class FixtureWeKnoraBackend:
    def list_document_chunks(self, external_doc_id: str) -> list[dict[str, Any]]:
        if external_doc_id != "wk-doc-fixture":
            raise SmokeError(f"unexpected external_doc_id: {external_doc_id}")
        return [
            {
                "id": "wk-chunk-001",
                "external_doc_id": external_doc_id,
                "chunk_index": 2,
                "title": "Fixture Chunk",
                "content": "sanitized chunk excerpt one",
                "content_hash": "hash-one",
                "token_count": 4,
                "char_count": 27,
                "start_char": 10,
                "end_char": 37,
                "source": "weknora_api",
                "metadata": {
                    "weknora_chunk_type": "text",
                    "weknora_knowledge_base_id": "kb-fixture",
                },
                "embedding_status": "indexed",
            },
            {
                "id": "wk-chunk-002",
                "external_doc_id": external_doc_id,
                "chunk_index": 3,
                "title": "Fixture Chunk",
                "content": "sanitized chunk excerpt two",
                "content_hash": "hash-two",
                "token_count": 4,
                "char_count": 27,
                "start_char": 38,
                "end_char": 65,
                "source": "weknora_api",
                "metadata": {"weknora_chunk_type": "text"},
                "embedding_status": "indexed",
            },
        ]


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora chunks smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora chunks smoke passed (fixture)")
    print(f"- document id: {result['document_id']}")
    print(f"- first chunk id: {result['first_chunk_id']}")
    print(f"- total chunks: {result['total']}")
    print(f"- source: {result['source']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    original_backend_factory = document_service._weknora_backend
    document_service._weknora_backend = lambda: FixtureWeKnoraBackend()  # type: ignore[assignment]
    try:
        with TemporaryDirectory(prefix="pa-weknora-chunks-smoke-") as temp_dir:
            engine = create_engine(f"sqlite:///{Path(temp_dir) / 'smoke.db'}")
            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                document = Document(
                    title="Fixture Document",
                    knowledge_backend="weknora_api",
                    external_doc_id="wk-doc-fixture",
                    status="indexed",
                )
                session.add(document)
                session.commit()
                session.refresh(document)
                chunks = document_service.list_document_chunks(session, document.id)
                reads = [DocumentChunkRead.model_validate(chunk) for chunk in chunks]
                if len(reads) != 2:
                    raise SmokeError(f"expected 2 chunks, got {len(reads)}")
                first = reads[0]
                if first.id != "wk-chunk-001":
                    raise SmokeError(f"unexpected chunk id: {first.id}")
                if first.external_doc_id != "wk-doc-fixture":
                    raise SmokeError(f"unexpected external doc id: {first.external_doc_id}")
                if first.start_char != 10 or first.end_char != 37:
                    raise SmokeError("chunk offsets were not mapped")
                if first.source != "weknora_api" or first.embedding_status != "indexed":
                    raise SmokeError("chunk source/status were not mapped")
                if not first.metadata_json or "weknora_chunk_type" not in first.metadata_json:
                    raise SmokeError("WeKnora metadata was not preserved")
                if "sanitized chunk excerpt" not in first.content:
                    raise SmokeError("chunk excerpt was not mapped")
                return {
                    "document_id": document.id,
                    "first_chunk_id": first.id,
                    "total": len(reads),
                    "source": first.source,
                }
    finally:
        document_service._weknora_backend = original_backend_factory  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())
