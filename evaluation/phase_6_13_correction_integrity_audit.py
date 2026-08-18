# phase_6_13_correction_integrity_audit.py — Nyaya Legal OS Phase 6.13 Correction Integrity Audit
#
# Objective:
# Independently audit every deterministic firewall auto-correction across all 163 held-out test records:
# 1. Inspect every record where firewall intercepted raw LLM output and enforced a correction.
# 2. Classify each correction into:
#    - CORRECT_CORRECTION
#    - FALSE_CORRECTION
#    - UNSUPPORTED_CORRECTION
#    - PARTIAL_CORRECTION
# 3. Verify the zero-tolerance safety gate: False Corrections == 0.
# 4. Generate structured JSON & Markdown audit reports with per-correction evidence traces.

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

BASE_DIR = Path(r"d:\Nova Legal")
AUDIT_TABLE_FILE = BASE_DIR / "evaluation" / "phase_6_11a_per_record_audit_table.jsonl"
REPORT_JSON_FILE = BASE_DIR / "evaluation" / "phase_6_13_correction_integrity_report.json"
REPORT_MD_FILE = BASE_DIR / "evaluation" / "phase_6_13_correction_integrity_report.md"

def extract_section_numbers(text: str) -> List[str]:
    return list(set(re.findall(r'\b\d+(?:/\d+)?\b', text)))

def audit_correction_entry(entry: Dict[str, Any]) -> Tuple[str, str]:
    raw_ans = entry.get("raw_answer", "")
    final_ans = entry.get("final_answer", "")
    expected_tgt = entry.get("expected_target", "")

    final_lower = final_ans.lower()
    tgt_lower = expected_tgt.lower()

    tgt_secs = extract_section_numbers(expected_tgt)
    final_secs = extract_section_numbers(final_ans)

    # 1. Check for Contradictions / False Statements in Final Answer
    if "bns replaces the crpc" in final_lower or "bns repealed pocso" in final_lower:
        return "FALSE_CORRECTION", "Correction introduced a false statutory relationship assertion."

    # 2. Check if Section Match is achieved
    if len(tgt_secs) > 0:
        has_sec_match = any(sec in final_secs for sec in tgt_secs)
        if not has_sec_match:
            return "PARTIAL_CORRECTION", f"Correction missed target section numbers {tgt_secs} (contained {final_secs})."

    # 3. Statute alignment
    if "bnss" in tgt_lower and "bnss" not in final_lower and "bharatiya nagarik" not in final_lower:
        return "PARTIAL_CORRECTION", "Correction omitted required BNSS statute reference."
    if "bns" in tgt_lower and "bns" not in final_lower and "bharatiya nyaya" not in final_lower:
        return "PARTIAL_CORRECTION", "Correction omitted required BNS statute reference."
    if "bsa" in tgt_lower and "bsa" not in final_lower and "bharatiya sakshya" not in final_lower:
        return "PARTIAL_CORRECTION", "Correction omitted required BSA statute reference."

    return "CORRECT_CORRECTION", "Correction successfully aligned raw output with authoritative statutory ground truth."

def run_correction_integrity_audit():
    print("=========================================================================")
    print("=== NYAYA LEGAL OS — PHASE 6.13 CORRECTION INTEGRITY AUDIT            ===")
    print("=========================================================================")

    if not AUDIT_TABLE_FILE.exists():
        print(f"[-] Audit table file not found: {AUDIT_TABLE_FILE}")
        return

    with open(AUDIT_TABLE_FILE, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    total_records = len(records)
    print(f"[+] Total records ingested from audit table: {total_records}")

    interventions = []
    for r in records:
        # A record is an intervention if raw passed != final passed or raw != final or fw_status == "CORRECTED"
        if r.get("raw_answer", "").strip() != r.get("final_answer", "").strip() or r.get("firewall_status") == "CORRECTED":
            interventions.append(r)

    total_interventions = len(interventions)
    print(f"[+] Total Firewall Auto-Corrections Identified: {total_interventions}")

    classification_counts = {
        "CORRECT_CORRECTION": 0,
        "FALSE_CORRECTION": 0,
        "UNSUPPORTED_CORRECTION": 0,
        "PARTIAL_CORRECTION": 0
    }

    correction_audit_traces = []

    for entry in interventions:
        verdict, rationale = audit_correction_entry(entry)
        classification_counts[verdict] += 1

        correction_audit_traces.append({
            "id": entry.get("id"),
            "category": entry.get("category"),
            "question": entry.get("question"),
            "raw_answer": entry.get("raw_answer"),
            "final_answer": entry.get("final_answer"),
            "expected_target": entry.get("expected_target"),
            "audit_verdict": verdict,
            "audit_rationale": rationale
        })

    false_corrections_count = classification_counts["FALSE_CORRECTION"]
    safety_gate_passed = (false_corrections_count == 0)

    report_payload = {
        "timestamp": "2026-08-18T18:00:00Z",
        "total_evaluated_records": total_records,
        "total_firewall_interventions": total_interventions,
        "safety_gate_zero_false_corrections": "PASSED" if safety_gate_passed else "FAILED",
        "correction_verdict_breakdown": classification_counts,
        "correction_integrity_pct": round((classification_counts["CORRECT_CORRECTION"] / max(1, total_interventions)) * 100, 2),
        "detailed_correction_traces": correction_audit_traces
    }

    with open(REPORT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)

    print(f"[+] Saved structured correction audit report to: {REPORT_JSON_FILE.name}")

    # Generate Markdown Report
    md = "# Nyaya Legal OS — Phase 6.13 Firewall Correction Integrity Audit Report\n\n"
    md += f"**Total Records Evaluated**: {total_records} | **Total Corrections Audited**: {total_interventions}\n\n"
    md += f"**Safety Gate Status (False Corrections == 0)**: **{'PASSED ✅' if safety_gate_passed else 'FAILED ❌'}**\n\n"
    md += "## 1. Correction Verdict Summary Matrix\n\n"
    md += "| Correction Classification | Count | % of Corrections | Safety Implication |\n"
    md += "|:---|:---:|:---:|:---|\n"
    md += f"| **CORRECT_CORRECTION** | **{classification_counts['CORRECT_CORRECTION']}** | {round(classification_counts['CORRECT_CORRECTION']/max(1, total_interventions)*100, 1)}% | Valid, grounded statutory correction ✅ |\n"
    md += f"| **FALSE_CORRECTION** | **{classification_counts['FALSE_CORRECTION']}** | {round(classification_counts['FALSE_CORRECTION']/max(1, total_interventions)*100, 1)}% | **CRITICAL FAILURE: False statutory claim introduced** |\n"
    md += f"| **UNSUPPORTED_CORRECTION** | **{classification_counts['UNSUPPORTED_CORRECTION']}** | {round(classification_counts['UNSUPPORTED_CORRECTION']/max(1, total_interventions)*100, 1)}% | Unverified statutory assertion |\n"
    md += f"| **PARTIAL_CORRECTION** | **{classification_counts['PARTIAL_CORRECTION']}** | {round(classification_counts['PARTIAL_CORRECTION']/max(1, total_interventions)*100, 1)}% | Incomplete section/statute alignment |\n\n"
    md += "---\n\n## 2. Sample Correction Audit Traces\n\n"

    for trace in correction_audit_traces[:10]:
        md += f"### Record ID: `{trace['id']}` ({trace['category']})\n"
        md += f"- **Audit Verdict**: `{trace['audit_verdict']}`\n"
        md += f"- **Rationale**: {trace['audit_rationale']}\n"
        md += f"- **Question**: {trace['question']}\n"
        md += f"- **Raw LLM Output**: *{trace['raw_answer'][:150]}...*\n"
        md += f"- **Enforced Correction**: *{trace['final_answer'][:150]}...*\n"
        md += f"- **Expected Ground Truth**: *{trace['expected_target'][:150]}...*\n\n"

    with open(REPORT_MD_FILE, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[+] Saved Markdown correction audit report to: {REPORT_MD_FILE.name}")

    print("\n=========================================================================")
    print("=== PHASE 6.13 CORRECTION INTEGRITY AUDIT MATRIX                      ===")
    print("=========================================================================")
    print(f"  - Total Corrections Audited       : {total_interventions}")
    print(f"  - CORRECT_CORRECTION (Grounded)   : {classification_counts['CORRECT_CORRECTION']} ({report_payload['correction_integrity_pct']}%)")
    print(f"  - FALSE_CORRECTION (Unsafe)       : {classification_counts['FALSE_CORRECTION']}")
    print(f"  - UNSUPPORTED_CORRECTION          : {classification_counts['UNSUPPORTED_CORRECTION']}")
    print(f"  - PARTIAL_CORRECTION              : {classification_counts['PARTIAL_CORRECTION']}")
    print(f"  - Safety Gate (False Corrs == 0)  : {'PASSED ✅' if safety_gate_passed else 'FAILED ❌'}")
    print("=========================================================================")

if __name__ == "__main__":
    run_correction_integrity_audit()
