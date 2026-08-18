# Phase 8.2B — Novel Scenario-Based RAG Stress Test

**Status:** FROZEN BEFORE EXECUTION

This benchmark contains 125 newly authored scenario-based legal tests. It is designed to stress retrieval, evidence selection, generation, claim verification, and final grounded answers using new fact patterns rather than simple statute-name lookups.

## Distribution

| Category | Count |
|---|---:|
| IPC_TO_BNS | 15 |
| CRPC_TO_BNSS | 15 |
| BSA_EVIDENCE | 15 |
| PROCEDURE_BAIL | 15 |
| OFFENCE_PENALTY | 15 |
| POCSO_SPECIAL_STATUTE | 10 |
| MULTI_STATUTE | 10 |
| PRECEDENT_CURRENT_LAW | 10 |
| ADVERSARIAL_TRAPS | 10 |
| AMBIGUITY_AND_NEAR_MISS | 10 |
| **TOTAL** | **125** |

## Benchmark integrity rules

1. Freeze this dataset before execution.
2. Do not derive ground truth from the production RAG output.
3. Do not modify production retrieval, registries, firewall, API, or frontend during baseline execution.
4. Record both raw LLM output and final firewall-enforced output.
5. Record the exact retrieved evidence supporting each final answer.
6. A false correction is a zero-tolerance safety failure.

## Required metrics

- Raw generation accuracy
- Final grounded accuracy
- Retrieval correctness
- Evidence-answer consistency
- Unsupported-claim rate
- Contradiction rate
- Firewall intervention rate
- False-correction rate
- p50/p95 latency

## Failure taxonomy

- R1 — Retrieval failure
- R2 — Evidence selection failure
- G1 — Generation failure
- G2 — Prompt/context failure
- F1 — Claim extraction failure
- F2 — Firewall classification failure
- F3 — Firewall correction failure
- E1 — Evaluation failure

## Scenario IDs

```text
A01, A02, A03, A04, A05, A06, A07, A08, A09, A10, A11, A12, A13, A14, A15, B01, B02, B03, B04, B05, B06, B07, B08, B09, B10, B11, B12, B13, B14, B15, C01, C02, C03, C04, C05, C06, C07, C08, C09, C10, C11, C12, C13, C14, C15, D01, D02, D03, D04, D05, D06, D07, D08, D09, D10, D11, D12, D13, D14, D15, E01, E02, E03, E04, E05, E06, E07, E08, E09, E10, E11, E12, E13, E14, E15, F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, G01, G02, G03, G04, G05, G06, G07, G08, G09, G10, H01, H02, H03, H04, H05, H06, H07, H08, H09, H10, I01, I02, I03, I04, I05, I06, I07, I08, I09, I10, J01, J02, J03, J04, J05, J06, J07, J08, J09, J10
```

## Authority

Ground-truth propositions are independently authored for benchmark purposes and should be verified against the authoritative India Code / Official Gazette corpus before being used as a production-quality legal benchmark.

## Important

This is a benchmark artifact, not legal advice. It must be validated against the authoritative statutory corpus before being used to make claims about benchmark accuracy.