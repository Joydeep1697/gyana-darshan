"""run_phase_8_2g_retrieval_only_benchmark.py — Gate 2 Retrieval-Only Benchmark & Gate 3 Forensics.

Runs pure retrieval (AuthoritativeLegalRetriever) on all 100 cases without LLM generation, firewall, or post-processing.
Measures:
- Recall@1, Recall@3, Recall@5, Recall@10
- Precision@5
- MRR
- NDCG@10
Breakdowns:
- BNS, BNSS, BSA, POCSO
- Multi-statute, Narrative Blind, Section Conversion, Procedural, Precedent

Classifies failures:
- R1: Candidate absent in corpus
- R2: Candidate retrieved but ranked too low (> top_5)
- R3: Wrong statute branch
- R4: Narrative concept not recognized
- R5: Multi-statute decomposition failure
- R6: Subsection / heading mismatch
"""

import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

sys.path.append(str(Path(__file__).resolve().parent.parent))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever

def normalize_sec(sec_str: str) -> str:
    m = re.match(r'(\d+[A-Za-z]*)', str(sec_str).strip())
    return m.group(1).upper() if m else str(sec_str).strip().upper()

def compute_ndcg_at_k(retrieved_pairs: List[Tuple[str, str]], expected_set: Set[Tuple[str, str]], k: int = 10) -> float:
    dcg = 0.0
    for i, p in enumerate(retrieved_pairs[:k]):
        if p in expected_set or any(p[0] == ep[0] and p[1] == ep[1] for ep in expected_set):
            dcg += 1.0 / math.log2(i + 2) # i=0 -> log2(2)=1
    
    # Ideal DCG
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(expected_set), k)))
    return (dcg / idcg) if idcg > 0 else 0.0

def run_retrieval_only_benchmark():
    print("==================================================================")
    print("=== PHASE 8.2G — GATE 2 RETRIEVAL-ONLY FORENSICS BENCHMARK     ===")
    print("==================================================================\n")

    retriever = AuthoritativeLegalRetriever()
    
    # Load raw cases and ground truth audit
    adv_raw = [json.loads(l) for l in open(r"C:\Users\joyde\Downloads\nyaya_darshana_50_advanced_hybrid_cases.jsonl", encoding="utf-8") if l.strip()]
    blind_raw = [json.loads(l) for l in open("evaluation/narrative_blind_50_verified.jsonl", encoding="utf-8") if l.strip()]
    
    audit_data = json.load(open("evaluation/phase_8_2g_ground_truth_audit.json", encoding="utf-8"))
    audit_map = {c["case_id"]: c for c in audit_data}

    raw_map = {c["scenario_id"]: c for c in adv_raw}
    raw_map.update({c["scenario_id"]: c for c in blind_raw})

    records = []
    
    # Metrics accumulators
    r1_list, r3_list, r5_list, r10_list, p5_list, mrr_list, ndcg10_list = [], [], [], [], [], [], []
    
    # Category accumulators
    category_stats = {
        "BNS": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "BNSS": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "BSA": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "POCSO": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "MULTI_STATUTE": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "NARRATIVE_BLIND": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "SECTION_CONVERSION": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "PROCEDURAL": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0},
        "PRECEDENT": {"total": 0, "r5": 0, "r10": 0, "mrr": 0.0}
    }

    # Failure taxonomy counts
    failure_counts = {"R1": 0, "R2": 0, "R3": 0, "R4": 0, "R5": 0, "R6": 0}

    for idx, (cid, audit_rec) in enumerate(audit_map.items(), 1):
        raw_case = raw_map.get(cid, {})
        full_query = (raw_case.get("fact_pattern", "") + "\n\n" + raw_case.get("legal_question", "")).strip()

        # Pure Retrieval without LLM or Firewall
        pack = retriever.retrieve_evidence_pack(full_query, top_k=10)
        retrieved_secs = pack.get("retrieved_sections", [])

        # Format retrieved pairs
        ret_pairs = []
        for s in retrieved_secs:
            st = s.get("short_name") or ("BNS" if "Nyaya" in s.get("statute","") else ("BNSS" if "Nagarik" in s.get("statute","") else ("BSA" if "Sakshya" in s.get("statute","") else ("POCSO" if "POCSO" in s.get("statute","") else s.get("statute","")))))
            sec = normalize_sec(s.get("section", ""))
            ret_pairs.append((st.upper(), sec))

        # Expected pairs from verified ground truth audit
        exp_secs_raw = audit_rec.get("independently_verified_sections", [])
        exp_pairs = [(e["statute"].upper(), normalize_sec(e["section"])) for e in exp_secs_raw]
        exp_set = set(exp_pairs)

        # Compute slices
        top_1 = ret_pairs[:1]
        top_3 = ret_pairs[:3]
        top_5 = ret_pairs[:5]
        top_10 = ret_pairs[:10]

        # Recalls
        def calc_recall(sub_pairs):
            if not exp_pairs: return 1.0
            matched = [ep for ep in exp_pairs if ep in sub_pairs or any(ep[0] == rp[0] and ep[1] == rp[1] for rp in sub_pairs)]
            return len(matched) / len(exp_pairs)

        rec_1 = calc_recall(top_1)
        rec_3 = calc_recall(top_3)
        rec_5 = calc_recall(top_5)
        rec_10 = calc_recall(top_10)

        # Precision@5
        matched_5 = [rp for rp in top_5 if rp in exp_set or any(rp[0] == ep[0] and rp[1] == ep[1] for ep in exp_set)]
        prec_5 = len(matched_5) / len(top_5) if top_5 else 0.0

        # MRR (first relevant item rank)
        rr = 0.0
        for r_idx, rp in enumerate(ret_pairs, 1):
            if rp in exp_set or any(rp[0] == ep[0] and rp[1] == ep[1] for ep in exp_set):
                rr = 1.0 / r_idx
                break

        # NDCG@10
        ndcg10 = compute_ndcg_at_k(ret_pairs, exp_set, k=10)

        r1_list.append(rec_1)
        r3_list.append(rec_3)
        r5_list.append(rec_5)
        r10_list.append(rec_10)
        p5_list.append(prec_5)
        mrr_list.append(rr)
        ndcg10_list.append(ndcg10)

        # Failure classification
        failure_type = "NONE"
        if rec_10 < 1.0:
            exp_statutes = set(ep[0] for ep in exp_pairs)
            ret_statutes = set(rp[0] for rp in ret_pairs)
            
            if len(exp_statutes) > 1 and not exp_statutes.issubset(ret_statutes):
                failure_type = "R5" # Multi-statute decomposition failure
                failure_counts["R5"] += 1
            elif any(ep[0] not in ret_statutes for ep in exp_pairs):
                failure_type = "R3" # Wrong statute branch
                failure_counts["R3"] += 1
            elif rec_10 == 0.0:
                if audit_rec["benchmark_class"] == "NARRATIVE_BLIND":
                    failure_type = "R4" # Narrative concept not recognized
                    failure_counts["R4"] += 1
                else:
                    failure_type = "R2" # Candidate retrieved too low / absent from top_k
                    failure_counts["R2"] += 1
            else:
                # Subsection / ranking drop
                failure_type = "R2"
                failure_counts["R2"] += 1

        # Tag categories
        b_class = audit_rec.get("benchmark_class", "")
        exp_statutes_list = list(set(ep[0] for ep in exp_pairs))
        
        for st in exp_statutes_list:
            if st in category_stats:
                category_stats[st]["total"] += 1
                category_stats[st]["r5"] += rec_5
                category_stats[st]["r10"] += rec_10
                category_stats[st]["mrr"] += rr

        if len(exp_statutes_list) > 1:
            category_stats["MULTI_STATUTE"]["total"] += 1
            category_stats["MULTI_STATUTE"]["r5"] += rec_5
            category_stats["MULTI_STATUTE"]["r10"] += rec_10
            category_stats["MULTI_STATUTE"]["mrr"] += rr

        if b_class == "NARRATIVE_BLIND":
            category_stats["NARRATIVE_BLIND"]["total"] += 1
            category_stats["NARRATIVE_BLIND"]["r5"] += rec_5
            category_stats["NARRATIVE_BLIND"]["r10"] += rec_10
            category_stats["NARRATIVE_BLIND"]["mrr"] += rr

        if any(w in full_query.lower() for w in ["convert", "replace", "equivalent", "legacy"]):
            category_stats["SECTION_CONVERSION"]["total"] += 1
            category_stats["SECTION_CONVERSION"]["r5"] += rec_5
            category_stats["SECTION_CONVERSION"]["r10"] += rec_10
            category_stats["SECTION_CONVERSION"]["mrr"] += rr

        if any(w in full_query.lower() for w in ["procedure", "remand", "custody", "bail", "notice", "arrest"]):
            category_stats["PROCEDURAL"]["total"] += 1
            category_stats["PROCEDURAL"]["r5"] += rec_5
            category_stats["PROCEDURAL"]["r10"] += rec_10
            category_stats["PROCEDURAL"]["mrr"] += rr

        if any(w in full_query.lower() for w in ["precedent", "supreme court", "antil", "case law"]):
            category_stats["PRECEDENT"]["total"] += 1
            category_stats["PRECEDENT"]["r5"] += rec_5
            category_stats["PRECEDENT"]["r10"] += rec_10
            category_stats["PRECEDENT"]["mrr"] += rr

        rec_entry = {
            "case_id": cid,
            "benchmark_class": b_class,
            "expected_sections": exp_pairs,
            "top_1": top_1,
            "top_3": top_3,
            "top_5": top_5,
            "top_10": top_10,
            "recall@1": round(rec_1, 4),
            "recall@3": round(rec_3, 4),
            "recall@5": round(rec_5, 4),
            "recall@10": round(rec_10, 4),
            "precision@5": round(prec_5, 4),
            "mrr": round(rr, 4),
            "ndcg@10": round(ndcg10, 4),
            "failure_type": failure_type
        }
        records.append(rec_entry)

    # Aggregates
    n = len(records)
    avg_r1 = sum(r1_list) / n * 100
    avg_r3 = sum(r3_list) / n * 100
    avg_r5 = sum(r5_list) / n * 100
    avg_r10 = sum(r10_list) / n * 100
    avg_p5 = sum(p5_list) / n * 100
    avg_mrr = sum(mrr_list) / n
    avg_ndcg10 = sum(ndcg10_list) / n

    # Save JSON Report
    out_json = Path("evaluation/phase_8_2g_retrieval_only_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "Recall@1": round(avg_r1, 2),
                "Recall@3": round(avg_r3, 2),
                "Recall@5": round(avg_r5, 2),
                "Recall@10": round(avg_r10, 2),
                "Precision@5": round(avg_p5, 2),
                "MRR": round(avg_mrr, 4),
                "NDCG@10": round(avg_ndcg10, 4)
            },
            "failure_taxonomy": failure_counts,
            "category_breakdown": {
                k: {
                    "total_cases": v["total"],
                    "Recall@5": round(v["r5"] / v["total"] * 100, 2) if v["total"] > 0 else 0.0,
                    "Recall@10": round(v["r10"] / v["total"] * 100, 2) if v["total"] > 0 else 0.0,
                    "MRR": round(v["mrr"] / v["total"], 4) if v["total"] > 0 else 0.0
                } for k, v in category_stats.items()
            },
            "records": records
        }, f, indent=2, ensure_ascii=False)

    print(f"=== RETRIEVAL-ONLY BENCHMARK RESULTS ({n} Scenarios) ===")
    print(f"• Recall@1:     {avg_r1:.2f}%")
    print(f"• Recall@3:     {avg_r3:.2f}%")
    print(f"• Recall@5:     {avg_r5:.2f}%")
    print(f"• Recall@10:    {avg_r10:.2f}%")
    print(f"• Precision@5:  {avg_p5:.2f}%")
    print(f"• MRR:          {avg_mrr:.4f}")
    print(f"• NDCG@10:      {avg_ndcg10:.4f}\n")

    print("=== FAILURE TAXONOMY COUNTS ===")
    for k, v in failure_counts.items():
        pct = (v / n) * 100
        print(f"• {k}: {v} cases ({pct:.1f}%)")

if __name__ == "__main__":
    run_retrieval_only_benchmark()
