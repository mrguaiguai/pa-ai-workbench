# Phase 3 M3 RAG Quality Sample Report

This sample report is generated from the P3-M3-C2 synthetic golden set and the
P3-M3-C3 rubric fixture. It is an offline contract report, not a live WeKnora
quality claim.

## Summary

- Cases evaluated: 4
- Backend: `golden_fixture`
- Mean recall proxy: 1.00
- Citation traceability pass rate: 1.00
- Source diversity pass rate: 1.00
- Average latency: 715 ms
- Average manual rating: 4.62
- Overall pass: yes

## Case Results

| Case | Task | Recall proxy | Citation traceability | Source diversity | Latency | Manual rating | Diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gq-001-retention-controls` | knowledge QA | 1.00 | 1.00 | 1.00 | 620 ms | 4.83 | healthy |
| `gq-002-incident-exception` | policy analysis | 1.00 | 1.00 | 1.00 | 740 ms | 4.50 | healthy |
| `gq-003-case-follow-up` | case review | 1.00 | 1.00 | 1.00 | 690 ms | 4.67 | healthy |
| `gq-004-wiki-draft-sources` | wiki draft | 1.00 | 1.00 | 1.00 | 810 ms | 4.50 | healthy |

## Reviewer Notes

- The report passes because the fixture evidence covers every required term,
  expected source type, and traceable citation condition.
- The sample observations intentionally keep latency below the target so the
  report demonstrates the metric shape, not live performance.
- A live pilot report must replace `golden_fixture` observations with
  `weknora_api` observations and preserve the same diagnosis buckets.
