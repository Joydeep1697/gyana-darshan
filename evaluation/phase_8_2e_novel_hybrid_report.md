# NYAYA DARSHANA — PHASE 8.2E NOVEL HYBRID LEGAL RAG DIAGNOSTIC REPORT
**BENCHMARK RUN**: 100 Cases (`ADV-001` to `ADV-050` Hybrid Adversarial + `BLIND-001` to `BLIND-050` Narrative Blind)  
**PROTOCOL**: STRICT ENGINEERING CONTROL PROTOCOL (RULES 0 THROUGH 30)  
**STATUS**: **DIAGNOSTIC BENCHMARK COMPLETE (ZERO CODE MODIFICATIONS)**  
**SAFETY GATE**: **0 False Corrections** across all 100 test scenarios  

---

## 1. EXECUTIVE DIAGNOSTIC SUMMARY

```text
========================================================================================================
                               PHASE 8.2E NOVEL HYBRID RAG DIAGNOSTIC MATRIX
========================================================================================================
Metric / Dimension                      Value                   Evaluation Standard / Target
────────────────────────────────────────────────────────────────────────────────────────────────────────
Total Scenarios Tested                  100 Cases               ADV-001 to ADV-050 & BLIND-001 to BLIND-050
Final Composite Legal Accuracy          31.50%                 Weighted (Pass=1.0, Partial=0.5, Fail=0)
Raw Model Accuracy                      31.50%                 Pre-firewall raw generation accuracy
Retrieval Section Precision             22.00%                 Relevant retrieved / Total retrieved
Retrieval Section Recall                27.34%                 Retrieved target sections / Total expected
────────────────────────────────────────────────────────────────────────────────────────────────────────
1. Statute Scope Identification         62.00%                 All required statutory regimes identified
2. Legal Element Accuracy               91.00%                 Statutory definitions and mens rea present
3. Fact Application & Correlation       96.00%                 Fact pattern tied to statutory rules
4. Multi-Statute Issue Coverage         62.00%                 Full cross-statute coverage (BNS/BNSS/BSA/POCSO)
5. Evidence Citation Support            90.00%                 Cited sections backed by retrieved corpus
6. Prohibited Claim Avoidance           100.00%                 0% false assertions or repealed law
7. Meaningful Uncertainty Handling      35.42%                 Proper factual qualifications expressed
────────────────────────────────────────────────────────────────────────────────────────────────────────
Firewall Interventions Count            1 Interventions       Automated grounding verifications
False Corrections Count                 0 False Corrs         ZERO TOLERANCE SAFETY GATE: PASS ✅
Mean Query Latency                      37.90 ms             p50: 33.01 ms | p95: 82.25 ms
========================================================================================================
NOVEL_RAG_DIAGNOSTIC_GATE: FAIL
========================================================================================================
```

---

## 2. DIAGNOSTIC ATTRIBUTION DISTRIBUTIONS

### A. Retrieval Diagnostics (Why sections were omitted)
* **R1 (Target Material Absent from Index/Corpus)**: **0 cases**
* **R2 (Relevant Material Retrieved but Sub-optimal Ranking)**: **17 cases**
* **R3 (Multi-Statute Retrieval Incompleteness)**: **30 cases** (Dominant bottleneck in 4+ issue cases)
* **R4 (Semantic / Narrative Keyword Gap)**: **18 cases** (BM25 keyword drop on informal blind facts)

### B. Generation Diagnostics
* **G1 (Hallucination / Prohibited Claim Assertion)**: **0 cases** (0 hallucinations)
* **G2 (Wrong Legal Reasoning on Facts)**: **0 cases**
* **G3 (Incomplete Multi-Step Reasoning)**: **21 cases**
* **G4 (Failure to Express Factual Uncertainty)**: **12 cases**

### C. Firewall Diagnostics
* **F1 (Claim Extraction Failure)**: **0 cases**
* **F2 (Incorrect Grounding Classification)**: **0 cases**
* **F3 (False Correction — Safety Violation)**: **0 cases** (0 false corrections)
* **F4 (Incomplete Grounding Correction)**: **0 cases**

---

## 3. WORST 20 SCENARIOS (DIAGNOSTIC FORENSICS)

| Case ID | Benchmark Class | Category | Recall | Precision | Verdict | Primary Attribution |
|:---:|:---:|---|:---:|:---:|:---:|:---:|
| `ADV-016` | HYBRID_ADVERSARIAL | Altercation Death vs Private D | 0.0% | 0.0% | FAIL | R4 |
| `ADV-018` | HYBRID_ADVERSARIAL | Cyber Personation & Fund Trans | 0.0% | 0.0% | FAIL | R4 |
| `ADV-021` | HYBRID_ADVERSARIAL | Special Statute Non-Repeal & P | 0.0% | 0.0% | FAIL | R3 |
| `ADV-031` | HYBRID_ADVERSARIAL | POCSO In-Camera Trial & Minor  | 0.0% | 0.0% | FAIL | R4 |
| `ADV-040` | HYBRID_ADVERSARIAL | Multi-Statute Semantic Decompo | 0.0% | 0.0% | FAIL | R3 |
| `ADV-044` | HYBRID_ADVERSARIAL | Arrest Safeguards & Reason Rec | 0.0% | 0.0% | FAIL | R4 |
| `ADV-047` | HYBRID_ADVERSARIAL | POCSO Multi-Jurisdiction Onlin | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-001` | NARRATIVE_BLIND | Retail Cash Theft | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-002` | NARRATIVE_BLIND | Arson Threat Extortion | 0.0% | 0.0% | FAIL | R4 |
| `BLIND-003` | NARRATIVE_BLIND | Armed Group Robbery / Dacoity | 0.0% | 0.0% | FAIL | R4 |
| `BLIND-004` | NARRATIVE_BLIND | Accountant Embezzlement & Forg | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-005` | NARRATIVE_BLIND | Fatal Rash Driving | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-006` | NARRATIVE_BLIND | Evaluate whether the resident  | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-007` | NARRATIVE_BLIND | Identify the civil and crimina | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-008` | NARRATIVE_BLIND | Examine the criminal elements  | 0.0% | 0.0% | FAIL | R4 |
| `BLIND-010` | NARRATIVE_BLIND | What penal offences are establ | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-011` | NARRATIVE_BLIND | Identify the criminal liabilit | 0.0% | 0.0% | FAIL | R4 |
| `BLIND-012` | NARRATIVE_BLIND | Analyze the penal provisions g | 0.0% | 0.0% | FAIL | R4 |
| `BLIND-013` | NARRATIVE_BLIND | Determine the criminal liabili | 0.0% | 0.0% | FAIL | R3 |
| `BLIND-014` | NARRATIVE_BLIND | Examine the penal offence comm | 0.0% | 0.0% | FAIL | R3 |

---

## 4. BEST 20 SCENARIOS (PERFECT REASONING & RETRIEVAL)

| Case ID | Benchmark Class | Category | Recall | Precision | Verdict | Multi-Statute Coverage |
|:---:|:---:|---|:---:|:---:|:---:|:---:|
| `ADV-027` | HYBRID_ADVERSARIAL | E-Commerce Cheating & Screensh | 100.0% | 75.0% | PASS | PASS |
| `ADV-010` | HYBRID_ADVERSARIAL | Warehouse Theft & Forensic Fin | 100.0% | 50.0% | PASS | PASS |
| `ADV-008` | HYBRID_ADVERSARIAL | Notice of Appearance & Arrest  | 100.0% | 50.0% | PASS | PASS |
| `ADV-001` | HYBRID_ADVERSARIAL | Public Contract Forgery & Elec | 83.3% | 100.0% | PASS | PASS |
| `ADV-004` | HYBRID_ADVERSARIAL | Altered Regulatory Notice & Fu | 80.0% | 66.7% | PASS | PASS |
| `ADV-006` | HYBRID_ADVERSARIAL | Extortion vs Lawful Debt Asser | 100.0% | 100.0% | PARTIAL | PASS |
| `ADV-009` | HYBRID_ADVERSARIAL | Statutory Transition & Savings | 100.0% | 50.0% | PARTIAL | PASS |
| `ADV-048` | HYBRID_ADVERSARIAL | Prolonged Custody Post Charge- | 75.0% | 50.0% | PARTIAL | PASS |
| `ADV-042` | HYBRID_ADVERSARIAL | Extortion vs Threat of Lawful  | 66.7% | 75.0% | PARTIAL | PASS |
| `ADV-025` | HYBRID_ADVERSARIAL | Cyber Extortion vs Lawful Cont | 66.7% | 75.0% | PARTIAL | PASS |
| `ADV-046` | HYBRID_ADVERSARIAL | Copy Hash Integrity vs Origina | 66.7% | 50.0% | PARTIAL | PASS |
| `ADV-035` | HYBRID_ADVERSARIAL | Digital Data Theft & Trade Sec | 66.7% | 50.0% | PARTIAL | PASS |
| `ADV-033` | HYBRID_ADVERSARIAL | Pre-2024 Cheating Transition & | 66.7% | 50.0% | PARTIAL | PASS |
| `ADV-043` | HYBRID_ADVERSARIAL | Screenshots & Forwarded Chat A | 66.7% | 33.3% | PARTIAL | PASS |
| `ADV-015` | HYBRID_ADVERSARIAL | Voyeurism & Hidden Camera Seiz | 66.7% | 33.3% | PARTIAL | PASS |
| `ADV-005` | HYBRID_ADVERSARIAL | Stalking & Electronic Attribut | 66.7% | 33.3% | PARTIAL | PASS |
| `BLIND-017` | NARRATIVE_BLIND | Evaluate the standard of gross | 50.0% | 50.0% | PARTIAL | PARTIAL |
| `ADV-038` | HYBRID_ADVERSARIAL | Subsection Penalty Precision & | 50.0% | 50.0% | PARTIAL | PASS |
| `ADV-007` | HYBRID_ADVERSARIAL | Undertrial Bail & Multi-Case D | 50.0% | 50.0% | PARTIAL | PASS |
| `ADV-003` | HYBRID_ADVERSARIAL | Homicide vs Private Defence &  | 50.0% | 50.0% | PARTIAL | PASS |

---

## 5. FINAL GATE EVALUATION

```text
===================================================================================
                    PHASE 8.2E NOVEL RAG DIAGNOSTIC GATE
===================================================================================
Final Legal Composite Accuracy: 31.50%
Retrieval Section Recall:       27.34%
False Corrections:              0 (Zero Tolerance Threshold = 0)
===================================================================================
NOVEL_RAG_DIAGNOSTIC_GATE: FAIL
===================================================================================
```
