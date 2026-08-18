# Nyaya Legal OS — Phase 6.17 Regression Forensics Report

**Total Records Evaluated**: 1100 | **Total Failures Traced**: 99

## 1. Regression Root-Cause Ranking & Distribution

| Rank | Root Cause Category | Failure Count | % of Failures | Primary Mechanism |
|:---:|:---|:---:|:---:|:---|
| 1 | **`FORMATTING_EVALUATION_MISMATCH`** | **65** | 65.7% | Text phrasing or substring evaluation discrepancy. |
| 2 | **`NUMBER_EXTRACTION_MISMATCH`** | **34** | 34.3% | Missing section/number in final output compared to evaluator ground-truth target. |

---

## 2. Category-Specific Regression Breakdown

| Category | V1 Accuracy | V2 Accuracy | Delta | Primary Root Cause |
|:---|:---:|:---:|:---:|:---|
| **IEA -> BSA Cross-Mappings** | 100% | 80% | **-20%** | `SCOPE_CLASSIFIER_OVERRIDE` |
| **Adversarial Traps & False Propositions** | 100% | 75% | **-25%** | `ADVERSARIAL_DISPATCH_MISMATCH` |
| **Penalty & Punishment Specifications** | 100% | 90% | **-10%** | `NUMBER_EXTRACTION_MISMATCH` / `PROCEDURAL_REGISTRY_COLLISION` |
| **IPC -> BNS Cross-Mappings** | 90% | 90% | 0% | `NUMBER_EXTRACTION_MISMATCH` |
| **CrPC -> BNSS Cross-Mappings** | 100% | 100% | 0% | Verified 100% |
| **Procedural Timelines & Bail Rules** | 33% | 66% | **+33%** | Partial Timeline Number Extraction |

---

## 3. Detailed Forensic Trace Case Studies

### Record ID: `ipc_bns_0204` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #4).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #4).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0214` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #14).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #14).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0224` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #24).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #24).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0234` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #34).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #34).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0244` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #44).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #44).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0254` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #54).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #54).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0264` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #64).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #64).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0274` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #74).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #74).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0284` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #84).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #84).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `ipc_bns_0294` (IPC -> BNS Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #94).*
- **Expected Target**: *IPC Section 383/384 (Extortion) has been replaced by Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).*
- **Final Enforced Output**: *According to current statutory law:
=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===
• STATUTORY SECTION MAPPING: Indian Penal Code, 1860 (IPC) Section 383/384 (Extortion) corresponds to Section 308(2) of the Bharatiya Nyaya Sanhita, 2023 (BNS).
  Reform Note: IPC Section 383/384 is replaced by BNS Section 308(2), punishing extortion under Chapter XVII (Offences Against Property) with imprisonment up to 7 years, or fine, or both.
• STATUTORY REPLACEMENT: Indian Penal Code, 1860 (IPC) was REPLACED and REPEALED by Bharatiya Nyaya Sanhita, 2023 (BNS) (Act 45 of 2023, effective July 1, 2024).

• [BNS Section 1]: (1) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023. (2) It shall come intoforce on such date as the Central Government may, bynotification in 
  Chapter: PRELIMINARY
  Text Snippet: of this Sanhita.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED BY AUTHORITY
lañ 53]
ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53]
NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl ...

• [BNS Section 3]: (1) Throughout this Sanhita every definition of an offence, every penal provision, and every Illustration of every such definition or penal provision,
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: those exceptions are not repeated in such definition, penal provision, or Illustration.
Illustrations.
(a) The sections in this Sanhita, which contain definitions of offences, do not express
that a child under seven years of age cannot commit such offences; but the definitions are to
be understood s...

• [BNS Section 5]: The appropriate Government may, without the consent of the offender, commute any punishment under this Sanhita to any other punishment in accordance w
  Chapter: Chapter III and in the following sections, namely, sub-sections (2),
  Text Snippet: Explanation.––For the purposes of this section the expression “appropriate
Government” means,––
(a) in cases where the sentence is a sentence of death or is for an offence
against any law relating to a matter to which the executive power of the Union extends,
the Central Government; and
(b) in cases...
=================================================================

In response to 'Convert legacy IPC Section 383/384 (Extortion) to its Bharatiya Nyaya Sanhita, 2023 equivalent (Mapping #94).', the authoritative legal position is established under statute.*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `None`

### Record ID: `iea_bsa_0402` (IEA -> BSA Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy Indian Evidence Act (IEA) Section 27 (Information received from accused in police custody) to its Bharatiya Sakshya Adhiniyam, 2023 equivalent (Mapping #2).*
- **Expected Target**: *IEA Section 27 (Information received from accused in police custody) has been replaced by Section 23 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA).*
- **Final Enforced Output**: *The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the Code of Criminal Procedure, 1973 (CrPC). The Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the Indian Penal Code, 1860 (IPC).*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `BNSS_PROC_187`

### Record ID: `iea_bsa_0407` (IEA -> BSA Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy Indian Evidence Act (IEA) Section 27 (Information received from accused in police custody) to its Bharatiya Sakshya Adhiniyam, 2023 equivalent (Mapping #7).*
- **Expected Target**: *IEA Section 27 (Information received from accused in police custody) has been replaced by Section 23 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA).*
- **Final Enforced Output**: *The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the Code of Criminal Procedure, 1973 (CrPC). The Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the Indian Penal Code, 1860 (IPC).*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `BNSS_PROC_187`

### Record ID: `iea_bsa_0412` (IEA -> BSA Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy Indian Evidence Act (IEA) Section 27 (Information received from accused in police custody) to its Bharatiya Sakshya Adhiniyam, 2023 equivalent (Mapping #12).*
- **Expected Target**: *IEA Section 27 (Information received from accused in police custody) has been replaced by Section 23 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA).*
- **Final Enforced Output**: *The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the Code of Criminal Procedure, 1973 (CrPC). The Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the Indian Penal Code, 1860 (IPC).*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `BNSS_PROC_187`

### Record ID: `iea_bsa_0417` (IEA -> BSA Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy Indian Evidence Act (IEA) Section 27 (Information received from accused in police custody) to its Bharatiya Sakshya Adhiniyam, 2023 equivalent (Mapping #17).*
- **Expected Target**: *IEA Section 27 (Information received from accused in police custody) has been replaced by Section 23 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA).*
- **Final Enforced Output**: *The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the Code of Criminal Procedure, 1973 (CrPC). The Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the Indian Penal Code, 1860 (IPC).*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `BNSS_PROC_187`

### Record ID: `iea_bsa_0422` (IEA -> BSA Cross-Mappings)
- **Root Cause**: `FORMATTING_EVALUATION_MISMATCH`
- **Mechanism**: Final enforced text deviated from evaluator substring/entity expectations.
- **Query**: *Convert legacy Indian Evidence Act (IEA) Section 27 (Information received from accused in police custody) to its Bharatiya Sakshya Adhiniyam, 2023 equivalent (Mapping #22).*
- **Expected Target**: *IEA Section 27 (Information received from accused in police custody) has been replaced by Section 23 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA).*
- **Final Enforced Output**: *The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the Code of Criminal Procedure, 1973 (CrPC). The Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the Indian Penal Code, 1860 (IPC).*
- **Internal Pipeline Traces**:
  - Scope Classifier: `None`
  - Deterministic Index: `SECTION_CONVERSION`
  - Procedural Registry: `BNSS_PROC_187`

