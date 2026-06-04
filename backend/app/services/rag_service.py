from app import pathing as _pathing  # noqa: F401

from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import Evidence


def retrieve_evidence(
    query: str,
    filters: dict | None = None,
    top_k: int = 8,
) -> list[Evidence]:
    engine = create_knowledge_engine()
    return engine.retrieve(
        query=query,
        filters=filters or {},
        top_k=top_k,
    )
