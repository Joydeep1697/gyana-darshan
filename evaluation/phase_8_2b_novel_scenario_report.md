# Phase 8.2B — Novel Scenario RAG Stress Test Forensic Report

**Timestamp**: `2026-08-18T14:24:53Z` | **Safety Gate (False Corrections == 0)**: **`PASSED (0 False Corrections) ✅`**

**Final Grounded Accuracy**: **`90.4%`** (`113 / 125`) | **Verdict**: **`PASS`**

---

## 1. Executive Summary & Required Metrics

| Metric | Result | Target / Safety Boundary |
|:---|:---:|:---:|
| **Total Novel Scenarios** | `125` | `125 Records` |
| **Raw LLM Accuracy** | `88.8%` | Baseline |
| **Final Grounded Accuracy** | **`90.4%`** | $\ge 80.0\%$ Generalization Target |
| **Retrieval Accuracy** | `88.0%` | Top-4 Gazette Sections |
| **Evidence Support Rate** | `88.0%` | Gazette Grounded |
| **Prohibited False Claims** | `5` | Adversarial Defense |
| **Firewall Interventions** | `22` | Auto-Corrections |
| **Correct Corrections** | `21` | Claim Verification |
| **Partial Corrections** | `1` | Refined Grounding |
| **FALSE CORRECTIONS** | **`0`** | **`0 (MANDATORY SAFETY GATE)`** |
| **p50 Latency** | `8.1 ms` | $< 50ms$ |
| **p95 Latency** | `19.4 ms` | $< 100ms$ |

---

## 2. Category Performance Matrix

| Statutory Category | Total | Raw Passed | Raw Acc | Final Passed | Final Acc | Ret Passed | Ret Acc | False Claims | FW Interventions | False Corrs |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `IPC_TO_BNS` | 15 | 15 | 100.0% | **15** | **100.0%** | 14 | 93.3% | 0 | 0 | **0** |
| `CRPC_TO_BNSS` | 15 | 13 | 86.7% | **13** | **86.7%** | 14 | 93.3% | 1 | 2 | **0** |
| `BSA_EVIDENCE` | 15 | 9 | 60.0% | **9** | **60.0%** | 12 | 80.0% | 4 | 0 | **0** |
| `PROCEDURE_BAIL` | 15 | 14 | 93.3% | **14** | **93.3%** | 13 | 86.7% | 0 | 5 | **0** |
| `OFFENCE_PENALTY` | 15 | 15 | 100.0% | **15** | **100.0%** | 15 | 100.0% | 0 | 0 | **0** |
| `POCSO_SPECIAL_STATUTE` | 10 | 9 | 90.0% | **10** | **100.0%** | 9 | 90.0% | 0 | 2 | **0** |
| `MULTI_STATUTE` | 10 | 10 | 100.0% | **10** | **100.0%** | 10 | 100.0% | 0 | 1 | **0** |
| `PRECEDENT_CURRENT_LAW` | 10 | 8 | 80.0% | **8** | **80.0%** | 7 | 70.0% | 0 | 3 | **0** |
| `ADVERSARIAL_TRAPS` | 10 | 8 | 80.0% | **9** | **90.0%** | 6 | 60.0% | 0 | 6 | **0** |
| `AMBIGUITY_AND_NEAR_MISS` | 10 | 10 | 100.0% | **10** | **100.0%** | 10 | 100.0% | 0 | 3 | **0** |

---

## 3. Failure Attribution Taxonomy

| Code | Failure Layer | Count | Description |
|:---:|:---|:---:|:---|
| `R1` | Retrieval failure (statute/section missed completely) | **`0`** | |
| `R2` | Evidence selection failure (partial section match) | **`8`** | |
| `G1` | Raw LLM generation failure (evidence present but unparsed) | **`4`** | |
| `G2` | Context / prompt formulation limitation | **`0`** | |
| `F1` | Claim extraction failure | **`0`** | |
| `F2` | Firewall classification failure | **`0`** | |
| `F3` | Firewall correction failure | **`0`** | |
| `E1` | Evaluation / ground-truth ambiguity | **`0`** | |

---

## 4. Failed Scenarios Breakdown

| Scenario ID | Category | Query Snippet | Failure Code | Root Cause |
|:---|:---|:---|:---:|:---|
| `B09` | `CRPC_TO_BNSS` | Police want to seize property believed to be connected with an offence... | `G1` | Ret: ['106', '105', '502', '170'] |
| `B13` | `CRPC_TO_BNSS` | A witness's statement to police was reduced to writing and the defence... | `R2` | Ret: ['180', '183', '509', '179'] |
| `C03` | `BSA_EVIDENCE` | A party alleges that an electronic signature on a digital record belon... | `R2` | Ret: ['62', '61', '62', '63'] |
| `C05` | `BSA_EVIDENCE` | A document is required by law to be attested and an attesting witness ... | `G1` | Ret: ['67', '67', '68', '69'] |
| `C06` | `BSA_EVIDENCE` | A party cannot locate an attesting witness to a document that requires... | `G1` | Ret: ['67', '68', '67', '69'] |
| `C07` | `BSA_EVIDENCE` | A public servant's electronic record made in discharge of official dut... | `G1` | Ret: ['29', '28', '35', '30'] |
| `C11` | `BSA_EVIDENCE` | A party seeks to prove a fact that is directly relevant to a matter in... | `R2` | Ret: ['62', '62', '63', '61'] |
| `C14` | `BSA_EVIDENCE` | A party claims that a fact is especially within the knowledge of the o... | `R2` | Ret: ['104', '106', '105', '104'] |
| `D15` | `PROCEDURE_BAIL` | A lawyer asks whether a procedural time limit can be inferred merely f... | `R2` | Ret: ['473', '469', '89', '518'] |
| `H09` | `PRECEDENT_CURRENT_LAW` | A lawyer asks for a current statutory provision and supplies an old Cr... | `R2` | Ret: ['422', '492', '385', '509'] |
| `H10` | `PRECEDENT_CURRENT_LAW` | A user asks whether a case-law proposition has been 'written word-for-... | `R2` | Ret: ['362', '196', '196', '24'] |
| `I06` | `ADVERSARIAL_TRAPS` | The question claims that BNSS is the 'BNS Criminal Procedure Code'. Ho... | `R2` | Ret: ['385', '19', '74'] |

---

## 5. Comparison: Frozen Benchmark V3 vs. Novel Scenario Benchmark

> [!IMPORTANT]
> These benchmarks are completely independent and must remain distinct.

| Benchmark Profile | Dataset Size | Accuracy | False Corrections | Purpose |
|:---|:---:|:---:|:---:|:---|
| **INTERNAL FROZEN BENCHMARK (V3)** | `1,100 Records` | **`96.36%`** (1060/1100) | `0` | Statutory coverage & regression baseline |
| **NOVEL SCENARIO GENERALIZATION** | `125 Records` | **`90.4%`** (113/125) | **`0`** | Out-of-distribution fact patterns & stress test |

