"""scratch_phase_8_2g_forensics.py — Agent 1 QA Data Forensics & Agent 2 Legal Provenance Auditor.

Audits all 100 benchmark records:
- ADV-001 to ADV-050
- BLIND-001 to BLIND-050

Validates:
1. Expected statutes & sections against Official Gazette Bare Acts (BNS, BNSS, BSA, POCSO).
2. Content completeness & semantic match to fact pattern.
3. Placeholder detection (e.g. generic templates, ungrounded synthetic records).
4. Ambiguity detection.
5. Legal provenance support from corpus Bare Acts.

Outputs:
- evaluation/phase_8_2g_ground_truth_forensics.jsonl (Agent 1)
- evaluation/phase_8_2g_ground_truth_forensics_report.md (Agent 1 Report)
- evaluation/phase_8_2g_provenance_audit.jsonl (Agent 2 Audit)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

BASE_DIR = Path(r"d:\Gyana Darshan")
CORPUS_DIR = BASE_DIR / "corpus_integrity"

# Load Bare Acts
corpus_records = {}
for cf in ["bns_2023_corpus.jsonl", "bnss_2023_corpus.jsonl", "bsa_2023_corpus.jsonl", "pocso_2012_corpus.jsonl"]:
    p = CORPUS_DIR / cf
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    statute_short = rec.get("short_name") or ("BNS" if "Nyaya" in rec.get("statute","") else ("BNSS" if "Nagarik" in rec.get("statute","") else ("BSA" if "Sakshya" in rec.get("statute","") else "POCSO")))
                    sec = str(rec.get("section", "")).strip().upper()
                    corpus_records[(statute_short.upper(), sec)] = rec

def normalize_sec(sec_str: str) -> str:
    m = re.match(r'(\d+[A-Za-z]*)', str(sec_str).strip())
    return m.group(1).upper() if m else str(sec_str).strip().upper()

# Load Original Benchmark GT
adv_gt = json.load(open(BASE_DIR / "evaluation" / "ground_truth_adv_50.json", encoding="utf-8"))
blind_gt = json.load(open(BASE_DIR / "evaluation" / "ground_truth_narrative_blind_50.json", encoding="utf-8"))

# Load Raw Scenario Texts
blind_raw_lines = [json.loads(l) for l in open(BASE_DIR / "evaluation" / "narrative_blind_50.jsonl", encoding="utf-8") if l.strip()]
blind_raw = {c["scenario_id"]: c for c in blind_raw_lines}

# Also check ADV scenarios from results_adv_50_validated.jsonl or benchmark
adv_raw = {}
adv_res_file = BASE_DIR / "evaluation" / "results_adv_50_validated.jsonl"
if adv_res_file.exists():
    for l in open(adv_res_file, encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            adv_raw[d.get("scenario_id")] = d

print(f"Loaded {len(corpus_records)} corpus sections across BNS, BNSS, BSA, POCSO.")
print(f"Loaded {len(adv_gt)} ADV GT records, {len(blind_gt)} BLIND GT records.")
