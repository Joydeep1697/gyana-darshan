# Nyaya Legal OS — Phase 6.12A Forensic Failure Distribution Report

**Total Evaluated Records**: 163 | **Passed**: 47 (28.83%) | **Failed**: 116 (71.17%)

## 1. Ranked Failure Class Distribution

| Rank | Failure Class | Count | % of Failures | Severity | Target Deterministic Fix |
|:---:|:---|:---:|:---:|:---:|:---|
| 1 | **Legal reasoning / procedural rules** | 50 | 43.1% | `Medium` | Structured procedural rule & evidence synthesizer |
| 2 | **Case-law precedent codification** | 40 | 34.48% | `High` | Precedent-to-statute ratio codification registry |
| 3 | **Section conversion** | 19 | 16.38% | `High` | Deterministic legacy-to-reformed section cross-mapping index |
| 4 | **Penalty/punishment** | 7 | 6.03% | `Critical` | Offence penalty metadata table in retrieval pack |

---

## 2. Deep Dive & Representative Case Studies

### Legal reasoning / procedural rules (50 Cases — 43.1%)
- **Severity**: `Medium`
- **Target Fix**: Structured procedural rule & evidence synthesizer

#### Representative Examples:

- **ID**: `legal_reas_0002`
  - **Question**: Analyze the following legal scenario under current Indian Statutory Law (Case #1):
Fact Pattern: An accused inflicts gra
  - **Expected Target**: Legal Analysis & Statutory Reasoning:
1. Applicable Statutory Authority: BNS Sections 38 to 44
2. Legal Analysis: Under 
  - **Generated Output**: The accused should be charged with assault on a person who has committed an offense punishable by death under section 14
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `legal_reas_0007`
  - **Question**: Analyze the following legal scenario under current Indian Statutory Law (Case #2):
Fact Pattern: An accused inflicts gra
  - **Expected Target**: Legal Analysis & Statutory Reasoning:
1. Applicable Statutory Authority: BNS Sections 38 to 44
2. Legal Analysis: Under 
  - **Generated Output**: The accused should be charged with assault on a person who has committed an offense punishable by death under section 14
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `legal_reas_0012`
  - **Question**: Analyze the following legal scenario under current Indian Statutory Law (Case #3):
Fact Pattern: An accused inflicts gra
  - **Expected Target**: Legal Analysis & Statutory Reasoning:
1. Applicable Statutory Authority: BNS Sections 38 to 44
2. Legal Analysis: Under 
  - **Generated Output**: The accused should be charged with assault on a person who has committed an offense punishable by death under section 14
  - **Firewall Status**: `PASS` (Allowed through without correction)

### Case-law precedent codification (40 Cases — 34.48%)
- **Severity**: `High`
- **Target Fix**: Precedent-to-statute ratio codification registry

#### Representative Examples:

- **ID**: `case_law_0005`
  - **Question**: Analyze the ratio decidendi of Satender Kumar Antil v. CBI (2022) 10 SCC 51 and explain its codification in current 2023
  - **Expected Target**: Precedent Analysis for Satender Kumar Antil v. CBI (2022) 10 SCC 51:
- Core Ratio Decidendi: Strict guidelines on bail c
  - **Generated Output**: To analyze the ratio decidendi of Satender Kumar Antil v. CBI (2022) 10 SCC 51 and its codification in current 2023 Indi
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `case_law_0010`
  - **Question**: Analyze the ratio decidendi of Satender Kumar Antil v. CBI (2022) 10 SCC 51 and explain its codification in current 2023
  - **Expected Target**: Precedent Analysis for Satender Kumar Antil v. CBI (2022) 10 SCC 51:
- Core Ratio Decidendi: Strict guidelines on bail c
  - **Generated Output**: To analyze the ratio decidendi of Satender Kumar Antil v. CBI (2022) 10 SCC 51 and its codification in current 2023 Indi
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `case_law_0015`
  - **Question**: Analyze the ratio decidendi of Satender Kumar Antil v. CBI (2022) 10 SCC 51 and explain its codification in current 2023
  - **Expected Target**: Precedent Analysis for Satender Kumar Antil v. CBI (2022) 10 SCC 51:
- Core Ratio Decidendi: Strict guidelines on bail c
  - **Generated Output**: To analyze the ratio decidendi of Satender Kumar Antil v. CBI (2022) 10 SCC 51 and its codification in current 2023 Indi
  - **Firewall Status**: `PASS` (Allowed through without correction)

### Section conversion (19 Cases — 16.38%)
- **Severity**: `High`
- **Target Fix**: Deterministic legacy-to-reformed section cross-mapping index

#### Representative Examples:

- **ID**: `crpc_bnss_0062`
  - **Question**: Convert legacy CrPC Section 353 (Pronouncement of judgment) to its Bharatiya Nagarik Suraksha Sanhita, 2023 equivalent (
  - **Expected Target**: CrPC Section 353 (Pronouncement of judgment) has been replaced by BNSS Section 354/392 of the Bharatiya Nagarik Suraksha
  - **Generated Output**: To convert the legacy CrPC Section 353 (Pronouncement of judgment) into its Bharatiya Nagarik Suraksha Sanhita, 2023 equ
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `crpc_bnss_0125`
  - **Question**: Convert legacy CrPC Section 353 (Pronouncement of judgment) to its Bharatiya Nagarik Suraksha Sanhita, 2023 equivalent (
  - **Expected Target**: CrPC Section 353 (Pronouncement of judgment) has been replaced by BNSS Section 354/392 of the Bharatiya Nagarik Suraksha
  - **Generated Output**: To convert the legacy CrPC Section 353 (Pronouncement of judgment) into its Bharatiya Nagarik Suraksha Sanhita, 2023 equ
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `crpc_bnss_0003`
  - **Question**: Convert legacy CrPC Section 167 (Police remand) to its Bharatiya Nagarik Suraksha Sanhita, 2023 equivalent (Scenario #1)
  - **Expected Target**: CrPC Section 167 (Police remand) has been replaced by BNSS Section 187 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (
  - **Generated Output**: Scenario #1: Police remand

In scenario #1, the police would first initiate a case through the police report system or a
  - **Firewall Status**: `PASS` (Allowed through without correction)

### Penalty/punishment (7 Cases — 6.03%)
- **Severity**: `Critical`
- **Target Fix**: Offence penalty metadata table in retrieval pack

#### Representative Examples:

- **ID**: `bns_sec_id_0119`
  - **Question**: Specify the statutory provision, chapter classification, and penalty for 'Extortion' (Variant #3) under Bharatiya Nyaya 
  - **Expected Target**: Under Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS), the offence of 'Extortion' is governed as follows:
1. C
  - **Generated Output**: Under the Bharatiya Nyaya Sanhita, Chapter III, the following provisions apply:

- General Exception: Any person who has
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `bns_sec_id_0169`
  - **Question**: Specify the statutory provision, chapter classification, and penalty for 'Extortion' (Variant #4) under Bharatiya Nyaya 
  - **Expected Target**: Under Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS), the offence of 'Extortion' is governed as follows:
1. C
  - **Generated Output**: Under the Bharatiya Nyaya Sanhita, Chapter III, the following provisions apply:

- General Exception: "For every such su
  - **Firewall Status**: `PASS` (Allowed through without correction)

- **ID**: `bns_sec_id_0219`
  - **Question**: Specify the statutory provision, chapter classification, and penalty for 'Extortion' (Variant #5) under Bharatiya Nyaya 
  - **Expected Target**: Under Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS), the offence of 'Extortion' is governed as follows:
1. C
  - **Generated Output**: Under the Bharatiya Nyaya Sanhita, Chapter III, there is no specific provision for 'Extortion'. However, if we consider 
  - **Firewall Status**: `PASS` (Allowed through without correction)

