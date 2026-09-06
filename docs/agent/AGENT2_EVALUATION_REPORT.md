# Agent 2 Evaluation Report — Interim

Recorded: 2026-09-05

## Implemented and tested

- Intake safety responses remain pre-retrieval, citation-free, quota-free, and persisted.
- Conservative answer verdicts distinguish fully verified deterministic output from model output that has only citation identity coverage.
- Material legal claims are extracted for duties, rights, liability, guilt/innocence, legality, jurisdiction, limitations, deadlines, enforceability, arrest, penalties, applicability, and related legal consequences.
- Claim verdicts distinguish `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, and `INSUFFICIENT_EVIDENCE`; answer states expose fully grounded, partial, insufficient, or conflict states.
- Citation coverage and fully supported-claim completeness are separate metrics.
- Consultation request/attempt IDs prevent stale response insertion; browser cancellation and timeout are logical client-side aborts that restore the original question.
- The experimental retriever preserves a meaningful legacy `score` alias for `branch_score`.

## Verification

- Focused grounding/API/authentication regression set: passed.
- Full suite: 137 passed, 1 warning, 3 subtests passed.
- The full-suite baseline failure was fixed with a compatible score contract.

## Not yet measured or implemented

- Independent proposition entailment for arbitrary model-generated claims.
- Jurisdiction hierarchy and temporal applicability verdicts as explicit claim fields.
- Multi-authority conflict resolution, quote/pincite verification, and a human-reviewed legal gold set.
- Retrieval Recall@K, Precision@K, MRR, and nDCG benchmarks.
- A 100-case benchmark and holdout evaluation.
- Cooperative server-side cancellation; the present cancellation is logical client-side rejection of late responses.
- Mobile viewport and authenticated browser-flow verification for the new states.

## Release recommendation

**DO NOT RELEASE** as a claim of comprehensive legal-verification reliability. The new gate materially reduces false fully-verified states, but the unmeasured components above remain required for that claim.
