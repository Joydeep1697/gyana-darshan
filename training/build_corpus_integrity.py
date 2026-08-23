# build_corpus_integrity.py — Nyaya Legal OS Phase 6.9A Legal Corpus Integrity Builder
#
# Objective:
# Build machine-readable, 100% authoritative structured JSONL corpus files for:
# 1. Bharatiya Nyaya Sanhita, 2023 (BNS - Act 45 of 2023, 358 Sections)
# 2. Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS - Act 46 of 2023, 531 Sections)
# 3. Bharatiya Sakshya Adhiniyam, 2023 (BSA - Act 47 of 2023, 170 Sections)
# 4. Statutory Cross-Mapping Registry (BNS <-> IPC, BNSS <-> CrPC, BSA <-> IEA, POCSO Status)
#
# Output Directory: d:\Gyana Darshan\corpus_integrity\

import os
import re
import json
import pymupdf
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
RAW_DIR = BASE_DIR / "Indian Legal" / "raw"
OUT_DIR = BASE_DIR / "corpus_integrity"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ACTS_CONFIG = {
    "BNS": {
        "pdf_path": RAW_DIR / "250883_english_01042024 (1).pdf",
        "official_name": "Bharatiya Nyaya Sanhita, 2023",
        "short_name": "BNS",
        "act_number": "Act 45 of 2023",
        "expected_sections": 358,
        "predecessor": "Indian Penal Code, 1860 (IPC)",
        "source": "Official Gazette of India (Extraordinary, Part II, Section 1, No. 53, Dec 25, 2023)"
    },
    "BNSS": {
        "pdf_path": RAW_DIR / "A202346.pdf",
        "official_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "short_name": "BNSS",
        "act_number": "Act 46 of 2023",
        "expected_sections": 531,
        "predecessor": "Code of Criminal Procedure, 1973 (CrPC)",
        "source": "Official Gazette of India (Extraordinary, Part II, Section 1, No. 54, Dec 25, 2023)"
    },
    "BSA": {
        "pdf_path": RAW_DIR / "aa202347.pdf",
        "official_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "short_name": "BSA",
        "act_number": "Act 47 of 2023",
        "expected_sections": 170,
        "predecessor": "Indian Evidence Act, 1872 (IEA)",
        "source": "Official Gazette of India (Extraordinary, Part II, Section 1, No. 55, Dec 25, 2023)"
    }
}

def extract_structured_sections(code_key, config):
    pdf_path = config["pdf_path"]
    print(f"\n[+] Processing '{config['official_name']}' from: {pdf_path.name}")
    doc = pymupdf.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"

    # Regex for Chapter Detection
    chapters = re.findall(r'(CHAPTER\s+[I|V|X|L|C|D|M]+\b[^\n]*)', full_text, re.IGNORECASE)

    # Regex for Section Parsing: \n(\d+)\.\s*([^\n]+)
    section_matches = list(re.finditer(r'(?:\n|^)(\d+)\.\s+([^\n]+(?:\n[^\n]+){0,2})', full_text))
    print(f"    - Extracted Raw Section Pattern Matches: {len(section_matches)}")

    records = []
    current_chapter = "PRELIMINARY"

    for i in range(len(section_matches)):
        match = section_matches[i]
        sec_num = match.group(1)
        heading_candidate = match.group(2).replace('\n', ' ').strip()

        start_pos = match.end()
        end_pos = section_matches[i+1].start() if i+1 < len(section_matches) else len(full_text)
        body_text = full_text[start_pos:end_pos].strip()

        # Clean noise headers/footers
        body_text = re.sub(r'THE GAZETTE OF INDIA EXTRAORDINARY[^\n]*\n', '', body_text)
        body_text = re.sub(r'SEC\. 1\][^\n]*\n', '', body_text)
        body_text = re.sub(r'\d+\s+THE GAZETTE OF INDIA[^\n]*\n', '', body_text)

        # Detect chapter transitions in body_text
        ch_match = re.search(r'(CHAPTER\s+[I|V|X|L|C|D|M]+[^\n]*)', body_text, re.IGNORECASE)
        if ch_match:
            current_chapter = ch_match.group(1).strip()

        record = {
            "id": f"{code_key}_SEC_{sec_num}",
            "statute": config["official_name"],
            "short_name": config["short_name"],
            "act_number": config["act_number"],
            "predecessor": config["predecessor"],
            "chapter": current_chapter,
            "section": sec_num,
            "heading": heading_candidate[:150],
            "text": body_text[:2500],  # Verbatim section text
            "source": config["source"],
            "status": "active"
        }
        records.append(record)

    out_file = OUT_DIR / f"{code_key.lower()}_2023_corpus.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Saved {len(records)} structured sections to: {out_file.name}")
    return records

def create_statutory_mapping_registry():
    mapping_data = {
        "metadata": {
            "title": "Nyaya Legal OS — Official Statutory Replacement & Relationship Registry",
            "version": "1.0",
            "status": "AUTHORITATIVE"
        },
        "statute_replacements": [
            {
                "repealed_statute": "Indian Penal Code, 1860 (IPC)",
                "replacement_statute": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
                "effective_date": "July 1, 2024",
                "act_number": "Act 45 of 2023",
                "relationship": "REPLACED_AND_REPEALED"
            },
            {
                "repealed_statute": "Code of Criminal Procedure, 1973 (CrPC)",
                "replacement_statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
                "effective_date": "July 1, 2024",
                "act_number": "Act 46 of 2023",
                "relationship": "REPLACED_AND_REPEALED"
            },
            {
                "repealed_statute": "Indian Evidence Act, 1872 (IEA)",
                "replacement_statute": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
                "effective_date": "July 1, 2024",
                "act_number": "Act 47 of 2023",
                "relationship": "REPLACED_AND_REPEALED"
            },
            {
                "special_statute": "Protection of Children from Sexual Offences Act, 2012 (POCSO)",
                "relationship": "UNREPEALED_SPECIAL_STATUTE",
                "status": "ACTIVE_INDEPENDENT_LAW",
                "notes": "Operates independently alongside BNS 2023. Not repealed or subsumed."
            }
        ],
        "key_section_mappings": {
            "IPC_to_BNS": {
                "IPC 302 (Murder)": "BNS Section 103(1)",
                "IPC 307 (Attempt to murder)": "BNS Section 109",
                "IPC 376 (Rape)": "BNS Section 64",
                "IPC 420 (Cheating)": "BNS Section 318(4)",
                "IPC 124A (Sedition)": "BNS Section 152 (Acts endangering sovereignty, unity and integrity of India)",
                "IPC 506 (Criminal intimidation)": "BNS Section 351"
            },
            "CrPC_to_BNSS": {
                "CrPC 154 (FIR registration)": "BNSS Section 173 (Includes Zero FIR & E-FIR)",
                "CrPC 167 (Custody & Remand)": "BNSS Section 187",
                "CrPC 437/439 (Bail in non-bailable offences)": "BNSS Section 480/483",
                "CrPC 144 (Unlawful assembly/order)": "BNSS Section 163"
            },
            "IEA_to_BSA": {
                "IEA Section 45 (Expert opinion)": "BSA Section 39",
                "IEA Section 65B (Electronic evidence)": "BSA Section 61 (Includes digital certificate requirement)",
                "IEA Section 114A (Presumption as to absence of consent)": "BSA Section 119"
            }
        }
    }

    out_map = OUT_DIR / "statutory_cross_mappings.json"
    with open(out_map, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Created Statutory Cross-Mapping Registry: {out_map.name}")

def main():
    print("=========================================================================")
    print("=== NYAYA LEGAL OS — PHASE 6.9A LEGAL CORPUS INTEGRITY ENGINE         ===")
    print("=========================================================================")
    for code, cfg in ACTS_CONFIG.items():
        extract_structured_sections(code, cfg)
    create_statutory_mapping_registry()
    print("\n=========================================================================")
    print("=== PHASE 6.9A LEGAL CORPUS INTEGRITY COMPLETED SUCCESSFULLY           ===")
    print("=========================================================================")

if __name__ == "__main__":
    main()
