from fastapi import APIRouter

from app.schemas import EvidenceRead
from app.schemas import RagRetrieveRequest
from app.schemas import RagRetrieveResponse
from app.services.rag_service import retrieve_evidence
from knowledge_engine.schemas import Evidence

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/retrieve", response_model=RagRetrieveResponse)
def retrieve_rag_evidence(request: RagRetrieveRequest) -> RagRetrieveResponse:
    evidence_items = retrieve_evidence(
        query=request.query,
        filters=request.filters,
        top_k=request.top_k,
    )
    return RagRetrieveResponse(
        items=[_to_read_model(evidence) for evidence in evidence_items],
        total=len(evidence_items),
        query=request.query,
        filters=request.filters,
        top_k=request.top_k,
    )


def _to_read_model(evidence: Evidence) -> EvidenceRead:
    return EvidenceRead(
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        wiki_page_id=evidence.wiki_page_id,
        title=evidence.title,
        text=evidence.text,
        score=evidence.score,
        source=evidence.source,
        metadata=evidence.metadata,
    )
