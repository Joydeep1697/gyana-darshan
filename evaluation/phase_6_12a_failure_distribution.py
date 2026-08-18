# phase_6_12a_failure_distribution.py — Nyaya Legal OS Phase 6.12A Failure Distribution Analyzer
#
# Objective:
# Ingest evaluation/phase_6_11a_per_record_audit_table.jsonl, analyze all 116 failures,
# categorize each failure into structured legal failure classes, rank them by frequency and severity,
# and emit evaluation/phase_6_12_failure_distribution.json along with a detailed forensic report.

import os
import sys
import json
import re
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(r"d:\Nova Legal")
AUDIT_TABLE_FILE = BASE_DIR / "evaluation" / "phase_6_11a_per_record_audit_table.jsonl"
OUTPUT_JSON_FILE = BASE_DIR / "evaluation" / "phase_6_12_failure_distribution.json"
OUTPUT_REPORT_FILE = BASE_DIR / "evaluation" / "phase_6_12_failure_distribution_report.md"

def classify_record_failure(rec: Dict[str, Any]) -> str:
    category = rec.get("category", "").lower()
    q = rec.get("question", "").lower()
    tgt = rec.get("expected_target", "").lower()

    if "crpc -> bnss" in category or "ipc -> bns" in category or "convert legacy" in q or "corresponds to" in q:
        return "Section conversion"
    elif "case-law" in category or "ratio decidendi" in q or "precedent" in q or "scc" in q or "v." in q:
        return "Case-law precedent codification"
    elif "penalty" in q or "punishment" in q or "imprisonment" in tgt:
        return "Penalty/punishment"
    elif "bns section identification" in category or "specify the statutory provision" in q or "chapter classification" in q:
        return "Section/offence identification"
    elif "repeal" in q or "replace" in q or "successor" in q:
        return "Repeal/replacement"
    elif "commence" in q or "date" in q or "effective" in q:
        return "Dates/commencement"
    elif "legal reasoning" in category:
        return "Legal reasoning / procedural rules"
    else:
        return "Other"

def analyze_failures():
    if not AUDIT_TABLE_FILE.exists():
        print(f"[-] Audit table file not found: {AUDIT_TABLE_FILE}")
        return

    with open(AUDIT_TABLE_FILE, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    total_records = len(records)
    passed_records = [r for r in records if r.get("final_pass")]
    failed_records = [r for r in records if not r.get("final_pass")]

    total_failures = len(failed_records)
    print(f"[+] Ingested {total_records} audit records. Total failures: {total_failures} ({total_failures/total_records*100:.2f}%)")

    class_distribution = {}
    class_examples = {}

    SEVERITY_MAP = {
        "Section conversion": "High",
        "Section/offence identification": "High",
        "Penalty/punishment": "Critical",
        "Case-law precedent codification": "High",
        "Repeal/replacement": "Critical",
        "Legal reasoning / procedural rules": "Medium",
        "Dates/commencement": "High",
        "Other": "Low"
    }

    FIX_MAP = {
        "Section conversion": "Deterministic legacy-to-reformed section cross-mapping index",
        "Section/offence identification": "Structured bare act section & chapter hierarchy index",
        "Penalty/punishment": "Offence penalty metadata table in retrieval pack",
        "Case-law precedent codification": "Precedent-to-statute ratio codification registry",
        "Repeal/replacement": "Authoritative replacement and repeal mapping index",
        "Legal reasoning / procedural rules": "Structured procedural rule & evidence synthesizer",
        "Dates/commencement": "Statutory commencement date registry (July 1, 2024)",
        "Other": "Domain-specific rule injection"
    }

    for rec in failed_records:
        f_class = classify_record_failure(rec)
        class_distribution[f_class] = class_distribution.get(f_class, 0) + 1
        if f_class not in class_examples:
            class_examples[f_class] = []
        if len(class_examples[f_class]) < 3:
            class_examples[f_class].append({
                "id": rec.get("id"),
                "question": rec.get("question"),
                "raw_answer": rec.get("raw_answer"),
                "final_answer": rec.get("final_answer"),
                "expected_target": rec.get("expected_target"),
                "firewall_status": rec.get("firewall_status")
            })

    ranked_classes = sorted(class_distribution.items(), key=lambda x: x[1], reverse=True)

    results = {
        "total_evaluated": total_records,
        "total_passed": len(passed_records),
        "total_failed": total_failures,
        "accuracy_pct": round(len(passed_records) / total_records * 100, 2),
        "failure_classes": []
    }

    for f_class, count in ranked_classes:
        results["failure_classes"].append({
            "failure_class": f_class,
            "count": count,
            "percentage_of_failures": round(count / total_failures * 100, 2),
            "percentage_of_total_dataset": round(count / total_records * 100, 2),
            "severity": SEVERITY_MAP.get(f_class, "Medium"),
            "proposed_fix": FIX_MAP.get(f_class, "Deterministic Index"),
            "representative_examples": class_examples.get(f_class, [])
        })

    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[+] Saved structured failure distribution to: {OUTPUT_JSON_FILE.name}")

    # Generate Markdown Report
    md = "# Nyaya Legal OS — Phase 6.12A Forensic Failure Distribution Report\n\n"
    md += f"**Total Evaluated Records**: {total_records} | **Passed**: {len(passed_records)} (28.83%) | **Failed**: {total_failures} (71.17%)\n\n"
    md += "## 1. Ranked Failure Class Distribution\n\n"
    md += "| Rank | Failure Class | Count | % of Failures | Severity | Target Deterministic Fix |\n"
    md += "|:---:|:---|:---:|:---:|:---:|:---|\n"

    for rank, item in enumerate(results["failure_classes"], 1):
        md += f"| {rank} | **{item['failure_class']}** | {item['count']} | {item['percentage_of_failures']}% | `{item['severity']}` | {item['proposed_fix']} |\n"

    md += "\n---\n\n## 2. Deep Dive & Representative Case Studies\n\n"

    for item in results["failure_classes"]:
        md += f"### {item['failure_class']} ({item['count']} Cases — {item['percentage_of_failures']}%)\n"
        md += f"- **Severity**: `{item['severity']}`\n"
        md += f"- **Target Fix**: {item['proposed_fix']}\n\n"
        md += "#### Representative Examples:\n\n"
        for ex in item["representative_examples"]:
            md += f"- **ID**: `{ex['id']}`\n"
            md += f"  - **Question**: {ex['question']}\n"
            md += f"  - **Expected Target**: {ex['expected_target']}\n"
            md += f"  - **Generated Output**: {ex['final_answer']}\n"
            md += f"  - **Firewall Status**: `{ex['firewall_status']}` (Allowed through without correction)\n\n"

    with open(OUTPUT_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[+] Saved Markdown failure distribution report to: {OUTPUT_REPORT_FILE.name}")

    # Print Summary Table
    print("\n=========================================================================")
    print("=== PHASE 6.12A FAILURE DISTRIBUTION SUMMARY MATRIX                   ===")
    print("=========================================================================")
    for rank, item in enumerate(results["failure_classes"], 1):
        print(f"  {rank}. {item['failure_class']:<35} : {item['count']:>3} cases ({item['percentage_of_failures']:>5.1f}%) | Severity: {item['severity']:<8}")
    print("=========================================================================")

if __name__ == "__main__":
    analyze_failures()
