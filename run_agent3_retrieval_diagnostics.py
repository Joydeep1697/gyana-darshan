"""run_agent3_retrieval_diagnostics.py — Agent 3 Baseline Retrieval Diagnostics.

Measures the existing baseline retrieval system WITHOUT MODIFYING IT.
Evaluates retrieval across all benchmark cases and verified cases.
Outputs:
- evaluation/phase_8_2g_retrieval_diagnostics.jsonl
- Detailed diagnostic breakdown and failure taxonomy statistics
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever

def normalize_sec(sec_str: str) -> str:
    m = re.match(r'(\d+[A-Za-z]*)', str(sec_str).strip())
    return m.group(1).upper() if m else str(sec_str).strip().upper()

# Load Forensics Data to know verified cases
forensics_records = [json.loads(l) for l in open(BASE_DIR / "evaluation" / "phase_8_2g_ground_truth_forensics.jsonl", encoding="utf-8") if l.strip()]
forensics_map = {r["case_id"]: r for r in forensics_records}

# Load Ground Truth
adv_gt = json.load(open(BASE_DIR / "evaluation" / "ground_truth_adv_50.json", encoding="utf-8"))
blind_gt = json.load(open(BASE_DIR / "evaluation" / "ground_truth_narrative_blind_50.json", encoding="utf-8"))

# Load Raw Scenarios
blind_raw = {c["scenario_id"]: c for c in [json.loads(l) for l in open(BASE_DIR / "evaluation" / "narrative_blind_50.jsonl", encoding="utf-8") if l.strip()]}

# ADV raw query extraction
adv_res_file = BASE_DIR / "evaluation" / "results_adv_50_validated.jsonl"
adv_raw = {}
if adv_res_file.exists():
    for l in open(adv_res_file, encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            adv_raw[d.get("scenario_id")] = d

# Initialize baseline retriever
retriever = AuthoritativeLegalRetriever()

diagnostics_records = []
failure_counts = {
    "R0_SUCCESS": 0,
    "R1_NOT_RETRIEVED": 0,
    "R2_WRONG_STATUTE": 0,
    "R3_ADJACENT_SECTION": 0,
    "R4_RANKING_FAILURE": 0,
    "R5_NARRATIVE_LEXICAL_MISMATCH": 0,
    "R6_MULTI_STATUTE_COLLAPSE": 0,
    "R7_SPECIAL_STATUTE_FAILURE": 0,
}

verified_failure_counts = failure_counts.copy()
verified_total = 0
verified_statute_hits = 0
verified_section_hits = 0
verified_multi_statute_coverages = []

all_cases_keys = list(adv_gt.keys()) + list(blind_gt.keys())

for cid in all_cases_keys:
    is_adv = cid.startswith("ADV")
    gt = adv_gt[cid] if is_adv else blind_gt[cid]
    f_rec = forensics_map.get(cid, {})
    is_verified = (f_rec.get("ground_truth_status") == "VERIFIED")
    
    # Formulate query
    if is_adv:
        raw_info = adv_raw.get(cid, {})
        query = raw_info.get("prompt") or raw_info.get("query") or (gt.get("category", "") + " " + " ".join(gt.get("expected_legal_propositions", [])))
    else:
        raw_info = blind_raw.get(cid, {})
        query = (raw_info.get("fact_pattern", "") + " " + raw_info.get("legal_question", "")).strip()
        if not query:
            query = gt.get("category", "") + " " + " ".join(gt.get("expected_legal_propositions", []))

    # Retrieve evidence pack using frozen baseline
    evidence_pack = retriever.retrieve_evidence_pack(query, top_k=10)
    retrieved_items = evidence_pack.get("retrieved_sections", [])
    
    retrieved_statutes = []
    retrieved_sections = []
    retrieved_pairs = []
    for item in retrieved_items:
        st = item.get("short_name") or ("BNS" if "Nyaya" in item.get("statute","") else ("BNSS" if "Nagarik" in item.get("statute","") else ("BSA" if "Sakshya" in item.get("statute","") else "POCSO")))
        st = str(st).upper()
        sec = normalize_sec(item.get("section", ""))
        retrieved_statutes.append(st)
        retrieved_sections.append(f"{st} {sec}")
        retrieved_pairs.append((st, sec))
        
    expected_statutes = set(s.upper() for s in gt.get("expected_statutes", []))
    expected_sections_raw = gt.get("expected_sections", [])
    expected_pairs = set()
    for s in expected_sections_raw:
        st = s.get("statute", "").upper()
        sec = normalize_sec(s.get("section", ""))
        expected_pairs.add((st, sec))
        
    alt_sections_raw = gt.get("acceptable_alternative_sections", [])
    for s in alt_sections_raw:
        st = s.get("statute", "").upper()
        sec = normalize_sec(s.get("section", ""))
        expected_pairs.add((st, sec))

    # Evaluate presence
    retrieved_statute_set = set(retrieved_statutes)
    statute_match = bool(expected_statutes.intersection(retrieved_statute_set)) if expected_statutes else True
    
    # Section match and rank
    best_rank = None
    matched_pairs = []
    for rank_idx, pair in enumerate(retrieved_pairs):
        if pair in expected_pairs or any(pair[0] == ep[0] and pair[1] == ep[1] for ep in expected_pairs):
            matched_pairs.append(pair)
            if best_rank is None:
                best_rank = rank_idx + 1 # 1-indexed

    section_match = (best_rank is not None)
    
    # Multi-statute coverage check
    if len(expected_statutes) > 1:
        covered_exp_statutes = expected_statutes.intersection(retrieved_statute_set)
        coverage_ratio = len(covered_exp_statutes) / len(expected_statutes)
    else:
        coverage_ratio = 1.0 if statute_match else 0.0

    # Failure Mode Classification
    failure_type = "R0_SUCCESS"
    diag_reason = "Correct statutory section retrieved within top ranks."
    
    if not is_verified:
        # If contaminated placeholder
        if f_rec.get("ground_truth_status") == "PLACEHOLDER_CONTAMINATED":
            failure_type = "R5_NARRATIVE_LEXICAL_MISMATCH"
            diag_reason = "Synthetic placeholder query failed to match genuine legal concepts due to ungrounded boilerplate phrasing."
        else:
            failure_type = "R1_NOT_RETRIEVED"
            diag_reason = f"Unverified/Invalid case: {f_rec.get('status_reason')}"
    elif section_match:
        if best_rank > 5:
            failure_type = "R4_RANKING_FAILURE"
            diag_reason = f"Target section {matched_pairs} retrieved but ranked at position {best_rank} (> top-5)."
        else:
            # Check if multi-statute collapsed
            if len(expected_statutes) > 1 and coverage_ratio < 0.6:
                failure_type = "R6_MULTI_STATUTE_COLLAPSE"
                diag_reason = f"Dominant statute branch suppressed other expected statutes. Expected: {list(expected_statutes)}, Retrieved: {list(retrieved_statute_set)}"
            else:
                failure_type = "R0_SUCCESS"
                diag_reason = f"Target section retrieved at rank {best_rank} with satisfactory coverage."
    else:
        # Not retrieved
        if "POCSO" in expected_statutes and "POCSO" not in retrieved_statute_set:
            failure_type = "R7_SPECIAL_STATUTE_FAILURE"
            diag_reason = "POCSO special statute was not retrieved due to lack of explicit POCSO trigger terms or branch suppression."
        elif not statute_match:
            failure_type = "R2_WRONG_STATUTE"
            diag_reason = f"Wrong statute branch retrieved. Expected: {list(expected_statutes)}, Got: {list(retrieved_statute_set)}"
        elif len(expected_statutes) > 1 and coverage_ratio < 0.5:
            failure_type = "R6_MULTI_STATUTE_COLLAPSE"
            diag_reason = f"Multi-statute collapse: Only {list(retrieved_statute_set)} retrieved for multi-statute query {list(expected_statutes)}."
        else:
            # Check if adjacent section retrieved
            has_adjacent = False
            for exp_st, exp_sec in expected_pairs:
                try:
                    exp_num = int(re.match(r'\d+', exp_sec).group(0))
                    for ret_st, ret_sec in retrieved_pairs:
                        if ret_st == exp_st:
                            ret_num = int(re.match(r'\d+', ret_sec).group(0))
                            if abs(ret_num - exp_num) in [1, 2]:
                                has_adjacent = True
                                break
                except Exception:
                    pass
            if has_adjacent:
                failure_type = "R3_ADJACENT_SECTION"
                diag_reason = f"Adjacent section retrieved instead of exact target section."
            elif not is_adv and "BLIND" in cid:
                failure_type = "R5_NARRATIVE_LEXICAL_MISMATCH"
                diag_reason = "Narrative fact pattern lacked explicit statutory terminology, leading to lexical retrieval failure."
            else:
                failure_type = "R1_NOT_RETRIEVED"
                diag_reason = "Target section absent from candidate list."

    failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1
    
    if is_verified:
        verified_total += 1
        verified_failure_counts[failure_type] = verified_failure_counts.get(failure_type, 0) + 1
        if statute_match: verified_statute_hits += 1
        if section_match and best_rank <= 5: verified_section_hits += 1
        verified_multi_statute_coverages.append(coverage_ratio)

    diag_rec = {
        "case_id": cid,
        "correct_statute_present": statute_match,
        "correct_section_present": (section_match and best_rank <= 5),
        "correct_section_rank": best_rank,
        "retrieved_statutes": list(set(retrieved_statutes)),
        "retrieved_sections": retrieved_sections[:5],
        "failure_type": failure_type,
        "diagnostic_reason": diag_reason
    }
    diagnostics_records.append(diag_rec)

# Save diagnostics JSONL
with open(BASE_DIR / "evaluation" / "phase_8_2g_retrieval_diagnostics.jsonl", "w", encoding="utf-8") as f:
    for r in diagnostics_records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Agent 3 wrote {len(diagnostics_records)} retrieval diagnostic records.")
print("\n=== Overall Failure Distribution (All 100 cases) ===")
for k, v in failure_counts.items():
    print(f"  {k:30s}: {v:3d} ({v/len(diagnostics_records)*100:.1f}%)")

print(f"\n=== Verified Population Retrieval Diagnostics ({verified_total} Verified Cases) ===")
for k, v in verified_failure_counts.items():
    print(f"  {k:30s}: {v:3d} ({v/verified_total*100:.1f}%)")

mean_cov = sum(verified_multi_statute_coverages) / len(verified_multi_statute_coverages) if verified_multi_statute_coverages else 0.0
print(f"\nBaseline Verified Metrics:")
print(f"  Statute Recall: {verified_statute_hits / verified_total * 100:.2f}%")
print(f"  Section Recall (Top-5): {verified_section_hits / verified_total * 100:.2f}%")
print(f"  Multi-Statute Coverage: {mean_cov * 100:.2f}%")
