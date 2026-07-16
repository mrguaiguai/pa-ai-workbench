# Phase 3 M3 RAG Quality Evaluation Rubric

P3-M3-C3 defines one evaluation shape for PA RAG quality. It uses the
P3-M3-C2 synthetic golden set as the first offline input, then leaves the same
fields ready for live WeKnora pilot runs. The rubric measures retrieval
quality, citation quality, and usability without treating polished model prose
as proof that retrieval worked.

## Files

- `backend/fixtures/retrieval_quality_golden_m3.json`
- `backend/fixtures/rag_quality_evaluation_m3.json`
- `backend/scripts/smoke_rag_quality_evaluation_m3.py`
- `docs/PHASE3_M3_RAG_QUALITY_SAMPLE_REPORT.md`

## Metrics

| Metric | Area | How it is scored | Pass signal |
| --- | --- | --- | --- |
| `recall_proxy` | Retrieval quality | Required terms from `expected_citation_conditions` found in normalized PA `Evidence`. | At least `0.85` per case. |
| `citation_traceability` | Citation quality | PA `CitationChecker` validates that citations trace to document chunks or wiki pages. | `1.00`; any untraceable citation fails the case. |
| `source_diversity` | Retrieval quality | Expected source types and minimum distinct titles are represented. | At least `0.75` per case. |
| `latency` | Usability | Observed retrieval latency in milliseconds. | Target at or below `1500 ms`; warning at `2500 ms`. |
| `manual_rating` | Human review | Reviewer scores six dimensions from 1 to 5. | Average at least `4.0`. |

Manual review dimensions are `retrieval_fit`, `citation_usefulness`,
`answer_grounding`, `task_fit`, `material_sufficiency`, and
`reviewer_confidence`. A reviewer should score retrieval and evidence first,
then score answer quality only against the available evidence.

## Diagnosis Buckets

The acceptance flow must separate root causes instead of collapsing every poor
answer into "RAG is bad":

| Bucket | Primary signals | First action |
| --- | --- | --- |
| `configuration_problem` | Backend/model/KB readiness is false, or the backend returns a setup error before quality can be measured. | Fix configuration gates before evaluating retrieval quality. |
| `retrieval_problem` | Configuration is ready, but evidence misses required terms, source types, or source diversity. | Tune retrieval parameters, indexing, hybrid/rerank settings, or query routing. |
| `generation_problem` | Evidence passes, but the answer adds unsupported claims, omits citations, or fails citation traceability. | Adjust Agent prompts, citation policy, and faithfulness checks. |
| `material_quality_problem` | Retrieval and generation work, but indexed source material is incomplete, stale, or ambiguous. | Improve source documents, wiki pages, or content governance. |

## Contract

The C3 smoke is fixture-only. It does not call live WeKnora, does not read local
secrets, and does not claim production quality. It verifies that:

- the rubric fixture declares `recall_proxy`, `citation_traceability`,
  `source_diversity`, `latency`, and `manual_rating`;
- every C2 golden case has one sample observation;
- evidence is normalized through PA schema before scoring;
- citations are checked with PA `CitationChecker`;
- diagnostic scenarios cover `configuration_problem`, `retrieval_problem`,
  `generation_problem`, and `material_quality_problem`;
- the sample report matches deterministic metrics generated from the golden set.

Run:

```bash
backend/.venv/bin/python backend/scripts/smoke_rag_quality_evaluation_m3.py
```

Live pilot reports should use the same fields with `backend=weknora_api`,
separate retrieval latency from end-to-end Agent latency, and attach reviewer
notes without storing raw sensitive source material.
