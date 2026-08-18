# Phase 8.2B — Novel Scenario RAG Stress Test Forensic Report

**Timestamp**: `2026-08-18T14:04:34Z` | **Safety Gate (False Corrections == 0)**: **`FAILED ❌`**

**Final Grounded Accuracy**: **`49.6%`** (`62 / 125`) | **Verdict**: **`FAIL`**

---

## 1. Executive Summary & Required Metrics

| Metric | Result | Target / Safety Boundary |
|:---|:---:|:---:|
| **Total Novel Scenarios** | `125` | `125 Records` |
| **Raw LLM Accuracy** | `51.2%` | Baseline |
| **Final Grounded Accuracy** | **`49.6%`** | $\ge 80.0\%$ Generalization Target |
| **Retrieval Accuracy** | `43.2%` | Top-4 Gazette Sections |
| **Evidence Support Rate** | `43.2%` | Gazette Grounded |
| **Prohibited False Claims** | `3` | Adversarial Defense |
| **Firewall Interventions** | `34` | Auto-Corrections |
| **Correct Corrections** | `18` | Claim Verification |
| **Partial Corrections** | `14` | Refined Grounding |
| **FALSE CORRECTIONS** | **`2`** | **`0 (MANDATORY SAFETY GATE)`** |
| **p50 Latency** | `21.8 ms` | $< 50ms$ |
| **p95 Latency** | `28.4 ms` | $< 100ms$ |

---

## 2. Category Performance Matrix

| Statutory Category | Total | Raw Passed | Raw Acc | Final Passed | Final Acc | Ret Passed | Ret Acc | False Claims | FW Interventions | False Corrs |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `IPC_TO_BNS` | 15 | 10 | 66.7% | **9** | **60.0%** | 10 | 66.7% | 0 | 2 | **1** |
| `CRPC_TO_BNSS` | 15 | 11 | 73.3% | **11** | **73.3%** | 12 | 80.0% | 1 | 3 | **0** |
| `BSA_EVIDENCE` | 15 | 9 | 60.0% | **9** | **60.0%** | 8 | 53.3% | 2 | 1 | **0** |
| `PROCEDURE_BAIL` | 15 | 11 | 73.3% | **11** | **73.3%** | 10 | 66.7% | 0 | 6 | **0** |
| `OFFENCE_PENALTY` | 15 | 7 | 46.7% | **7** | **46.7%** | 7 | 46.7% | 0 | 0 | **0** |
| `POCSO_SPECIAL_STATUTE` | 10 | 4 | 40.0% | **4** | **40.0%** | 0 | 0.0% | 0 | 6 | **0** |
| `MULTI_STATUTE` | 10 | 0 | 0.0% | **0** | **0.0%** | 0 | 0.0% | 0 | 2 | **0** |
| `PRECEDENT_CURRENT_LAW` | 10 | 3 | 30.0% | **3** | **30.0%** | 2 | 20.0% | 0 | 4 | **0** |
| `ADVERSARIAL_TRAPS` | 10 | 4 | 40.0% | **3** | **30.0%** | 1 | 10.0% | 0 | 5 | **1** |
| `AMBIGUITY_AND_NEAR_MISS` | 10 | 5 | 50.0% | **5** | **50.0%** | 4 | 40.0% | 0 | 5 | **0** |

---

## 3. Failure Attribution Taxonomy

| Code | Failure Layer | Count | Description |
|:---:|:---|:---:|:---|
| `R1` | Retrieval failure (statute/section missed completely) | **`1`** | |
| `R2` | Evidence selection failure (partial section match) | **`58`** | |
| `G1` | Raw LLM generation failure (evidence present but unparsed) | **`2`** | |
| `G2` | Context / prompt formulation limitation | **`0`** | |
| `F1` | Claim extraction failure | **`0`** | |
| `F2` | Firewall classification failure | **`0`** | |
| `F3` | Firewall correction failure | **`2`** | |
| `E1` | Evaluation / ground-truth ambiguity | **`0`** | |

---

## 4. Failed Scenarios Breakdown

| Scenario ID | Category | Query Snippet | Failure Code | Root Cause |
|:---|:---|:---|:---:|:---|
| `A03` | `IPC_TO_BNS` | A person intentionally causes a non-fatal bodily injury without circum... | `R2` | Ret: ['117', '119', '121', '122'] |
| `A05` | `IPC_TO_BNS` | A person secretly takes another person's movable property without cons... | `F3` | Ret: ['303', '317', '30', '97'] |
| `A07` | `IPC_TO_BNS` | A person takes property from another by putting that person in fear of... | `R2` | Ret: ['28', '30', '32', '52'] |
| `A12` | `IPC_TO_BNS` | A person forges a document intending that it be used as genuine. Which... | `R2` | Ret: ['201', '241', '327', '509'] |
| `A13` | `IPC_TO_BNS` | A person knowingly uses a forged document as genuine. Which BNS provis... | `R2` | Ret: ['179', '182', '284', '81'] |
| `A15` | `IPC_TO_BNS` | A person publicly defames another by making or publishing an imputatio... | `R2` | Ret: ['351', '84', '115', '46'] |
| `B03` | `CRPC_TO_BNSS` | Police consider issuing a notice requiring a person to appear rather t... | `R2` | Ret: ['47', '60', '74', '84'] |
| `B09` | `CRPC_TO_BNSS` | Police want to seize property believed to be connected with an offence... | `G1` | Ret: ['106', '477', '4', '18'] |
| `B11` | `CRPC_TO_BNSS` | A court considers attaching property of a proclaimed person. Which BNS... | `R2` | Ret: ['86', '88', '243', '84'] |
| `B13` | `CRPC_TO_BNSS` | A witness's statement to police was reduced to writing and the defence... | `R2` | Ret: ['148', '319', '353', '55'] |
| `C03` | `BSA_EVIDENCE` | A party alleges that an electronic signature on a digital record belon... | `R2` | Ret: ['59', '86', '4', '201'] |
| `C06` | `BSA_EVIDENCE` | A party cannot locate an attesting witness to a document that requires... | `R2` | Ret: ['67', '327', '3', '256'] |
| `C09` | `BSA_EVIDENCE` | A party wants to rely on an authorised government publication containi... | `G1` | Ret: ['325', '32', '158', '153'] |
| `C11` | `BSA_EVIDENCE` | A party seeks to prove a fact that is directly relevant to a matter in... | `R2` | Ret: ['1', '14', '112', '3'] |
| `C12` | `BSA_EVIDENCE` | A prosecution relies on a statement made by an accused while in police... | `R2` | Ret: ['23', '181', '225', '230'] |
| `C15` | `BSA_EVIDENCE` | A party asserts a fact in issue and asks who bears the burden of provi... | `R2` | Ret: ['104', '109', '234', '269'] |
| `D05` | `PROCEDURE_BAIL` | An accused is served a notice of appearance and complies with it. What... | `R2` | Ret: ['347', '206', '261', '110'] |
| `D13` | `PROCEDURE_BAIL` | A witness's statement to police contains a significant omission and th... | `R2` | Ret: ['327', '181', '256', '264'] |
| `D14` | `PROCEDURE_BAIL` | A person is arrested for an offence and the defence asks whether the B... | `R2` | Ret: ['55', '83', '36', '37'] |
| `D15` | `PROCEDURE_BAIL` | A lawyer asks whether a procedural time limit can be inferred merely f... | `R2` | Ret: ['9', '52', '90', '172'] |
| `E01` | `OFFENCE_PENALTY` | A person threatens a victim to obtain delivery of money. No death or g... | `R2` | Ret: ['30', '66', '171', '232'] |
| `E06` | `OFFENCE_PENALTY` | A person is alleged to have intentionally caused the death of another ... | `R2` | Ret: ['102', '260', '395', '121'] |
| `E08` | `OFFENCE_PENALTY` | A person intentionally attempts to kill another, but the victim surviv... | `R2` | Ret: ['36', '265', '127', '46'] |
| `E10` | `OFFENCE_PENALTY` | A person takes property by putting the victim in fear of immediate har... | `R2` | Ret: ['34', '30', '32', '46'] |
| `E12` | `OFFENCE_PENALTY` | A person is alleged to have committed organised crime as defined by th... | `R2` | Ret: ['260', '46', '52', '56'] |
| `E13` | `OFFENCE_PENALTY` | A person is alleged to have committed a petty organised criminal activ... | `R2` | Ret: ['317', '260', '46', '52'] |
| `E14` | `OFFENCE_PENALTY` | A person is accused of a terrorist act as defined by the BNS. Which pr... | `R2` | Ret: ['241', '509', '115', '46'] |
| `E15` | `OFFENCE_PENALTY` | A person uses a dangerous weapon to cause hurt or grievous hurt. Which... | `R2` | Ret: ['119', '121', '122', '311'] |
| `F01` | `POCSO_SPECIAL_STATUTE` | A 15-year-old child is allegedly subjected to sexual assault. The inve... | `R2` | Ret: ['67', '94', '144', '225'] |
| `F03` | `POCSO_SPECIAL_STATUTE` | A child-protection case involves conduct potentially covered by both B... | `R2` | Ret: ['93', '225', '264', '402'] |
| `F04` | `POCSO_SPECIAL_STATUTE` | A lawyer asks whether a POCSO offence can be answered solely by retrie... | `R2` | Ret: ['245', '208', '362', '13'] |
| `F06` | `POCSO_SPECIAL_STATUTE` | A child victim case contains allegations of rape and the user asks whi... | `R1` | Ret: ['90', '193', '210', '212'] |
| `F08` | `POCSO_SPECIAL_STATUTE` | A query mentions both a child victim and an alleged general offence un... | `R2` | Ret: ['72', '182', '240', '219'] |
| `F09` | `POCSO_SPECIAL_STATUTE` | A false proposition says BNS Section 93 repealed POCSO. How should the... | `R2` | Ret: ['90', '227', '229', '230'] |
| `G01` | `MULTI_STATUTE` | A police investigation involves an alleged BNS offence, an arrest, and... | `R2` | Ret: ['46', '35', '37', '49'] |
| `G02` | `MULTI_STATUTE` | A suspect is arrested, police seize a laptop, and the prosecution seek... | `R2` | Ret: ['49', '106', '4', '46'] |
| `G03` | `MULTI_STATUTE` | A criminal case involves a confession, police custody, and an alleged ... | `R2` | Ret: ['232', '235', '384', '498'] |
| `G04` | `MULTI_STATUTE` | A trial concerns a forged electronic record allegedly used to cheat a ... | `R2` | Ret: ['206', '210', '241', '339'] |
| `G05` | `MULTI_STATUTE` | A victim alleges stalking and produces screenshots of repeated message... | `R2` | Ret: ['78', '3', '17', '46'] |
| `G06` | `MULTI_STATUTE` | A death case involves alleged murder, police remand, and a digital CCT... | `R2` | Ret: ['101', '180', '185', '196'] |
| `G07` | `MULTI_STATUTE` | A complainant asks about the offence, whether an FIR can be registered... | `R2` | Ret: ['183', '202', '208', '26'] |
| `G08` | `MULTI_STATUTE` | A case involves extortion, police seizure of property, and an electron... | `R2` | Ret: ['317', '351', '105', '106'] |
| `G09` | `MULTI_STATUTE` | A lawyer asks whether the same statute should supply the offence, arre... | `R2` | Ret: ['384', '319', '233', '242'] |
| `G10` | `MULTI_STATUTE` | A case includes a child victim, an arrest, and an electronic recording... | `R2` | Ret: ['209', '385', '478', '90'] |
| `H03` | `PRECEDENT_CURRENT_LAW` | A lawyer invokes D.K. Basu for safeguards concerning arrest and custod... | `R2` | Ret: ['265', '385', '40', '384'] |
| `H04` | `PRECEDENT_CURRENT_LAW` | A user asks whether Lalita Kumari is literally codified as a single BN... | `R2` | Ret: ['67', '89', '90', '172'] |
| `H05` | `PRECEDENT_CURRENT_LAW` | A user asks whether every principle from a Supreme Court case is autom... | `R2` | Ret: ['446', '9', '18', '26'] |
| `H07` | `PRECEDENT_CURRENT_LAW` | A user names a Supreme Court case but asks only for the current statut... | `R2` | Ret: ['91', '523', '25', '26'] |
| `H08` | `PRECEDENT_CURRENT_LAW` | A user asks whether a 2022 Supreme Court judgment was 'repealed' by BN... | `R2` | Ret: ['373', '15', '73', '137'] |
| `H09` | `PRECEDENT_CURRENT_LAW` | A lawyer asks for a current statutory provision and supplies an old Cr... | `R2` | Ret: ['422', '440', '492', '3'] |
| `H10` | `PRECEDENT_CURRENT_LAW` | A user asks whether a case-law proposition has been 'written word-for-... | `R2` | Ret: ['362', '72', '73', '172'] |
| `I01` | `ADVERSARIAL_TRAPS` | The question states: 'Since BNS is the new criminal code, it replaced ... | `R2` | Ret: ['19', '180', '195', '531'] |
| `I03` | `ADVERSARIAL_TRAPS` | The question states: 'BNS section 187 governs police custody.' Is that... | `R2` | Ret: ['40', '182', '191', '195'] |
| `I06` | `ADVERSARIAL_TRAPS` | The question claims that BNSS is the 'BNS Criminal Procedure Code'. Ho... | `R2` | Ret: ['19', '385', '156', '195'] |
| `I07` | `ADVERSARIAL_TRAPS` | The question claims extortion under BNS always carries death penalty. ... | `F3` | Ret: ['195', '4', '26', '27'] |
| `I08` | `ADVERSARIAL_TRAPS` | The question claims that every electronic record is automatically admi... | `R2` | Ret: ['63', '201', '85', '19'] |
| `I09` | `ADVERSARIAL_TRAPS` | The question claims that every police statement can be used substantiv... | `R2` | Ret: ['181', '239', '351', '47'] |
| `I10` | `ADVERSARIAL_TRAPS` | The query asks: 'Since the BNS commenced in 2024, every older criminal... | `R2` | Ret: ['6', '206', '392', '446'] |
| `J03` | `AMBIGUITY_AND_NEAR_MISS` | A user asks 'What replaced 302?' after discussing IPC offences. Which ... | `R2` | Ret: ['361', '244', '4', '3'] |
| `J04` | `AMBIGUITY_AND_NEAR_MISS` | A user asks 'What replaced 167?' after discussing police remand under ... | `R2` | Ret: ['182', '41', '72', '361'] |
| `J05` | `AMBIGUITY_AND_NEAR_MISS` | A user asks 'What replaced 65B?' while discussing electronic records u... | `R2` | Ret: ['1', '210', '244', '62'] |
| `J09` | `AMBIGUITY_AND_NEAR_MISS` | A user asks whether a CCTV clip proves the offence merely because it e... | `R2` | Ret: ['19', '35', '17', '26'] |
| `J10` | `AMBIGUITY_AND_NEAR_MISS` | A user asks whether a police search is lawful solely because the suspe... | `R2` | Ret: ['182', '35', '193', '168'] |

---

## 5. Comparison: Frozen Benchmark V3 vs. Novel Scenario Benchmark

> [!IMPORTANT]
> These benchmarks are completely independent and must remain distinct.

| Benchmark Profile | Dataset Size | Accuracy | False Corrections | Purpose |
|:---|:---:|:---:|:---:|:---|
| **INTERNAL FROZEN BENCHMARK (V3)** | `1,100 Records` | **`96.36%`** (1060/1100) | `0` | Statutory coverage & regression baseline |
| **NOVEL SCENARIO GENERALIZATION** | `125 Records` | **`49.6%`** (62/125) | **`0`** | Out-of-distribution fact patterns & stress test |

