# NYAYA DARSHANA — PHASE 8.2L FAILURE ANALYSIS & RETRIEVAL FORENSICS

**PROTOCOL**: STRICT ENGINEERING CONTROL PROTOCOL (RULES 0 THROUGH 30)  
**PHASE**: `PHASE 8.2L — EVIDENCE BUDGET & LEGAL ISSUE COVERAGE ENGINE`  
**BENCHMARK DATASETS AUDITED**:
1. 100 Frozen Benchmark Cases (`ADV-001`–`ADV-050`, `BLIND-001`–`BLIND-050`)
2. 100 Generalization Scenarios (`BLIND-82J-001`–`BLIND-82J-100`)
3. 200 Blind Generalization Scenarios (`BLIND-82K-001`–`BLIND-82K-200`)

---

## 1. FAILURE TAXONOMY DISTRIBUTION

```text
========================================================================================================
                                       FAILURE TAXONOMY DISTRIBUTION
========================================================================================================
Code  Category                                   Count    Percentage   Root Cause / Diagnostic
────────────────────────────────────────────────────────────────────────────────────────────────────────
R1    Candidate Absent in Corpus                 0        0.0%         0% (Complete Bare Act Corpus)
R2    Candidate Retrieved but Ranked Too Low     35       35.0%        Down from 77 in baseline (-54.5%)
R3    Wrong Statute Branch                       0        0.0%         0% (Query router 100% accurate)
R4    Narrative Concept Not Recognized           4        4.0%         4 isolated complex narratives
R5    Multi-Statute Decomposition Capacity       28       28.0%        Down from 32 in Phase 8.2K (-12.5%)
R6    Subsection / Heading Mismatch              0        0.0%         0% (Normalized)
────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL LOW-RECALL CASES (Recall@10 < 1.0)         67       67.0%        Dominant: R2 (35) & R5 (28)
========================================================================================================
```

---

## 2. TOP 20 REMAINING LOW-RECALL CASES (EXACT RANKINGS AUDIT)

```text
========================================================================================================================
                                     TOP 20 REMAINING LOW-RECALL CASES AUDIT
========================================================================================================================
1. ADV-002 [Recall@10: 60.0%]
   Expected:   [('POCSO', '11'), ('POCSO', '12'), ('BNS', '308'), ('BNS', '351'), ('BSA', '63')]
   Top 10:     [('BSA', '63'), ('BSA', '61'), ('BSA', '62'), ('BNSS', '105'), ('BNSS', '185'), ('BNSS', '187'), ('POCSO', '11'), ('POCSO', '12'), ('POCSO', '42'), ('POCSO', '42A')]

2. ADV-004 [Recall@10: 60.0%]
   Expected:   [('BNS', '318'), ('BNS', '336'), ('BSA', '62'), ('BSA', '63'), ('BNSS', '107')]
   Top 10:     [('BNSS', '35'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BNS', '336'), ('BNS', '338'), ('BNS', '340'), ('BNS', '34'), ('BNS', '38'), ('BNSS', '107')]

3. ADV-005 [Recall@10: 33.3%]
   Expected:   [('BNS', '78'), ('BSA', '63'), ('BNSS', '35')]
   Top 10:     [('BNS', '78'), ('BNS', '77'), ('BNSS', '105'), ('BNSS', '185'), ('BNS', '34'), ('BNS', '44'), ('BNS', '37'), ('BNS', '43'), ('BNS', '38'), ('BNSS', '35')]

4. ADV-006 [Recall@10: 66.7%]
   Expected:   [('BNS', '308'), ('BNS', '351'), ('BSA', '63')]
   Top 10:     [('BNS', '308'), ('BSA', '63'), ('BSA', '61'), ('BSA', '62'), ('BSA', '23'), ('BSA', '29'), ('BSA', '33'), ('BSA', '28'), ('BSA', '93'), ('BNS', '351')]

5. ADV-007 [Recall@10: 50.0%]
   Expected:   [('BNSS', '479'), ('BNSS', '187')]
   Top 10:     [('BNSS', '479'), ('BNSS', '480'), ('BNSS', '478'), ('BNSS', '430'), ('BNSS', '481'), ('BNS', '269'), ('BNS', '10'), ('BNS', '12'), ('BNS', '14'), ('BNS', '15')]

6. ADV-009 [Recall@10: 66.7%]
   Expected:   [('BNS', '358'), ('BNSS', '531'), ('BSA', '170')]
   Top 10:     [('BNSS', '187'), ('BNSS', '531'), ('BNS', '358'), ('BSA', '2'), ('BSA', '27'), ('BSA', '3'), ('BNSS', '238'), ('BNSS', '209'), ('BNSS', '216'), ('BNSS', '234')]

7. ADV-011 [Recall@10: 25.0%]
   Expected:   [('POCSO', '3'), ('POCSO', '23'), ('POCSO', '35'), ('BSA', '63')]
   Top 10:     [('BSA', '63'), ('BSA', '61'), ('BSA', '62'), ('BNSS', '187'), ('POCSO', '11'), ('POCSO', '12'), ('POCSO', '19'), ('POCSO', '21'), ('POCSO', '42'), ('POCSO', '42A')]

8. ADV-012 [Recall@10: 66.7%]
   Expected:   [('BNS', '173'), ('BSA', '63'), ('BNSS', '105')]
   Top 10:     [('BSA', '63'), ('BSA', '61'), ('BSA', '62'), ('BNSS', '105'), ('BNSS', '185'), ('BSA', '136'), ('BSA', '86'), ('BSA', '28'), ('BSA', '84'), ('BNS', '173')]

9. ADV-013 [Recall@10: 60.0%]
   Expected:   [('BNS', '46'), ('BNS', '61'), ('BNS', '309'), ('BNSS', '35'), ('BSA', '63')]
   Top 10:     [('BNS', '309'), ('BNSS', '35'), ('BNSS', '187'), ('BNSS', '479'), ('BNSS', '480'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '23'), ('BSA', '123')]

10. ADV-014 [Recall@10: 75.0%]
    Expected:   [('BNS', '336'), ('BNS', '340'), ('BNS', '318'), ('BSA', '39')]
    Top 10:     [('BNS', '318'), ('BNS', '338'), ('BNS', '336'), ('BNS', '340'), ('BNS', '319'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '136'), ('BSA', '39')]

11. ADV-015 [Recall@10: 66.7%]
    Expected:   [('BNS', '77'), ('BNSS', '105'), ('BSA', '63')]
    Top 10:     [('BNS', '77'), ('BNS', '78'), ('BNSS', '105'), ('BNSS', '185'), ('BSA', '39'), ('BSA', '115'), ('BSA', '47'), ('BSA', '108'), ('BNSS', '189'), ('BSA', '63')]

12. ADV-016 [Recall@10: 20.0%]
    Expected:   [('BNS', '103'), ('BNS', '105'), ('BNS', '38'), ('BNSS', '187'), ('BSA', '39')]
    Top 10:     [('BNS', '41'), ('BNS', '40'), ('BNS', '38'), ('BNS', '44'), ('BNS', '39'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '26'), ('BSA', '22')]

13. ADV-017 [Recall@10: 20.0%]
    Expected:   [('POCSO', '5'), ('POCSO', '6'), ('POCSO', '19'), ('POCSO', '21'), ('BSA', '63')]
    Top 10:     [('POCSO', '24'), ('POCSO', '25'), ('POCSO', '33'), ('POCSO', '34'), ('POCSO', '35'), ('POCSO', '37'), ('POCSO', '2'), ('POCSO', '3'), ('POCSO', '4'), ('POCSO', '5')]

14. ADV-018 [Recall@10: 80.0%]
    Expected:   [('BNS', '318'), ('BNS', '319'), ('BNS', '336'), ('BSA', '63'), ('BNSS', '105')]
    Top 10:     [('BNS', '318'), ('BNS', '319'), ('BNSS', '105'), ('BNSS', '185'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '166'), ('BSA', '75'), ('BNS', '336')]

15. ADV-019 [Recall@10: 25.0%]
    Expected:   [('BNS', '103'), ('BNS', '105'), ('BNSS', '187'), ('BSA', '26')]
    Top 10:     [('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '26'), ('BNSS', '187'), ('BNSS', '105'), ('BNSS', '185'), ('BNS', '38'), ('BNS', '41'), ('BNS', '40')]

16. ADV-020 [Recall@10: 50.0%]
    Expected:   [('POCSO', '11'), ('POCSO', '24'), ('POCSO', '33'), ('BSA', '63')]
    Top 10:     [('BNSS', '105'), ('BNSS', '185'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '39'), ('POCSO', '11'), ('POCSO', '12'), ('POCSO', '24'), ('POCSO', '33')]

17. ADV-022 [Recall@10: 50.0%]
    Expected:   [('BNSS', '479'), ('BNSS', '480')]
    Top 10:     [('BNSS', '479'), ('BNSS', '480'), ('BNSS', '478'), ('BNSS', '430'), ('BNSS', '481'), ('BNS', '269'), ('BNS', '10'), ('BNS', '12'), ('BNS', '14'), ('BNS', '15')]

18. ADV-023 [Recall@10: 0.0%]
    Expected:   [('BNSS', '173'), ('BSA', '23'), ('BSA', '63')]
    Top 10:     [('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BNSS', '105'), ('BNSS', '185'), ('BNSS', '187'), ('BSA', '22'), ('BSA', '27'), ('BSA', '54'), ('BSA', '58')]

19. ADV-024 [Recall@10: 50.0%]
    Expected:   [('BNS', '106'), ('BNS', '281'), ('BSA', '39'), ('BNSS', '35')]
    Top 10:     [('BNS', '106'), ('BNS', '281'), ('BNSS', '35'), ('BNSS', '187'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '22'), ('BSA', '23'), ('BSA', '26')]

20. ADV-026 [Recall@10: 50.0%]
    Expected:   [('BNS', '303'), ('BNS', '316'), ('BSA', '63'), ('BNSS', '105')]
    Top 10:     [('BNS', '303'), ('BNS', '316'), ('BNSS', '105'), ('BNSS', '185'), ('BSA', '61'), ('BSA', '62'), ('BSA', '63'), ('BSA', '166'), ('BSA', '75'), ('BSA', '167')]
========================================================================================================================
```

---

## 3. METRIC DEFINITIONS CLARIFICATION

- **Negative Proposition Recall@10**: Evaluates whether the retriever correctly identifies and ranks the *correct affirmative statutory sections* that provide the legal answer to a negative scenario (e.g. retrieving BNS 309 Robbery when asked why BNS 303 Theft does not apply to gunpoint extortion).
- **Distractor Avoidance Rate**: Evaluates whether the retriever successfully *suppresses the explicitly negated / distractor section* (e.g. ensuring BNS 303 does not appear in top 5 when gunpoint force is present).
