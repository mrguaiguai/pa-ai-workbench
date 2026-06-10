from app import pathing as _pathing  # noqa: F401

from knowledge_engine.evidence import normalize_evidence_results
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import Evidence


def retrieve_evidence(
    query: str,
    filters: dict | None = None,
    top_k: int = 8,
) -> list[Evidence]:
    engine = create_knowledge_engine()
    normalized_top_k = max(top_k, 0)
    return normalize_evidence_results(
        engine.retrieve(
            query=query,
            filters=filters or {},
            top_k=max(normalized_top_k * 2, normalized_top_k),
        ),
        top_k=normalized_top_k,
    )
