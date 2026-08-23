# Nyaya Darshana — Statutory Corpus Production Manifest

## Corpus Overview & Provenance Verification

This document establishes the official production manifest of the statutory legal corpus indexed within **Nyaya Darshana**.

- **Corpus Version**: `2026.08.18`
- **Engine Version**: `1.0.0`
- **Total Authoritative Section Records**: **1,353**
- **Extraction Protocol**: Direct text extraction from Official Gazette of India PDFs, segmented by section numbers, headings, sub-clauses, and statutory illustrations.

---

## Detailed Statute Breakdown

| Statute Name | Short Code | Act Number | Enactment | Effective Date | Predecessor Repealed | Section Records | Source Document Size | SHA256 Hash | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|:---:|
| **Bharatiya Nyaya Sanhita, 2023** | `BNS` | Act 45 of 2023 | 2023 | 2024-07-01 | Indian Penal Code, 1860 | **344** | 545,705 B | `97afd91af22a5659970d48b382b91fa2ae675dc9e4e7ed96c50004beb3eb0f31` | Verified ✅ |
| **Bharatiya Nagarik Suraksha Sanhita, 2023** | `BNSS` | Act 46 of 2023 | 2023 | 2024-07-01 | Code of Criminal Procedure, 1973 | **714** | 1,948,217 B | `54b27a4f2786dc5867c2cc23391e8359b3b29125684119acbc652d1630a716d6` | Verified ✅ |
| **Bharatiya Sakshya Adhiniyam, 2023** | `BSA` | Act 47 of 2023 | 2023 | 2024-07-01 | Indian Evidence Act, 1872 | **233** | 525,216 B | `993882ad0ae7ded6ae8087351edd61caeb6faa1a2d6c8fff8c269a9cf149b9ac` | Verified ✅ |
| **Protection of Children from Sexual Offences Act, 2012** | `POCSO` | Act 32 of 2012 | 2012 | 2012-11-14 | None (*Special Child Protection Statute; Overrides General Law per Sec 42A*) | **62** | 207,723 B | `def90f072fdb6b62fe95adafa0f5e1ef08f5f1002dbb6067f8af4b1cd94a5c5b` | Verified ✅ |
| **Total Production Corpus** | | | | | | **1,353** | **3,226,861 B** | | **Production Ready** |

---

## Corpus Integrity Audit

1. **Deterministic Cross-Mappings**:
   - IPC $\rightarrow$ BNS (Substantive offences and chapter numbers)
   - CrPC $\rightarrow$ BNSS (Procedural custody, remand, bail, judgment timelines)
   - IEA $\rightarrow$ BSA (Electronic records, primary/secondary evidence, confessions)
2. **Special Statute Interaction**:
   - POCSO Act 2012 is preserved as an active unrepealed special statute.
   - Section 42A of POCSO Act stipulates overriding effect over general criminal law provisions.
   - BNS Section 3(2) and Section 63/64/70 clarify that POCSO provisions and aggravated penalties apply for offences against children below 18 years of age.
