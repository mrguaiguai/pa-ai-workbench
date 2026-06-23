# Phase 3 M3 Retrieval Quality Golden Set

P3-M3-C2 adds a small, synthetic retrieval quality golden set for PA schema
regression. It is not live WeKnora evidence and it must not be treated as a
production quality score. The purpose is to make retrieval and citation
contract changes visible before live tuning starts.

## Files

- `backend/fixtures/retrieval_quality_golden_m3.json`
- `backend/scripts/smoke_retrieval_quality_golden_m3.py`

## Fixture Shape

Each case includes:

- `id`
- `task_type`
- `query`
- `top_k`
- `expected_citation_conditions`
- `human_note`
- `fixture_evidence`

The `expected_citation_conditions` block records the minimum acceptable
evidence count, expected `source_type` coverage, required terms, minimum source
title diversity, and whether traceable citations are required.

The fixture evidence is synthetic. Its source is `golden_fixture`, not
`weknora_api`, so the offline check cannot be mistaken for a live WeKnora
retrieval pass. Evidence items still use PA `Evidence` fields:
`evidence_id`, `source_type`, `document_id` or `external_doc_id`, `chunk_id`,
`wiki_page_id`, `title`, `text`, `score`, and citation metadata.

## Current Coverage

The initial set covers four public-affairs style paths:

- knowledge QA for retention controls;
- policy analysis for incident exceptions;
- case review follow-up checks;
- wiki draft source notes.

These cases are intentionally compact. They check whether retrieval results
contain the minimum information needed for a grounded answer, not whether a
specific backend rank exactly matches another backend.

## Evaluation

Run:

```bash
backend/.venv/bin/python backend/scripts/smoke_retrieval_quality_golden_m3.py
```

The smoke performs:

- fixture schema validation;
- high-confidence sensitive-token scan over the fixture;
- PA `Evidence` normalization;
- expected source type, required term, and source diversity checks;
- PA `CitationChecker` validation for traceable citations.

The result is an offline regression signal. Live quality tuning still needs
WeKnora-backed retrieval, real model gates, and human review.
