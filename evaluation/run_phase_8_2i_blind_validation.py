"""run_phase_8_2i_blind_validation.py — Evaluates 100-Scenario Blind Validation Set (Phase 8.2I).

Runs isolated AuthoritativeLegalRetriever on 100 brand-new unseen scenarios.
Measures:
- Recall@1, Recall@3, Recall@5, Recall@10
- Precision@5
- MRR
- NDCG@10
- Negative Distractor Avoidance Rate
- Category-level metrics (POCSO, BNS, BNSS, BSA, Multi-Statute, Negative Discrimination)
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
            dcg += 1.0 / math.log2(i + 2)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(expected_set), k)))
    return (dcg / idcg) if idcg > 0 else 0.0

def run_blind_validation():
    print("==================================================================")
    print("=== PHASE 8.2I — 100-SCENARIO BLIND GENERALIZATION BENCHMARK   ===")
    print("==================================================================\n")

    retriever = AuthoritativeLegalRetriever()
    cases = [json.loads(l) for l in open("evaluation/phase_8_2i_blind_validation_100.jsonl", encoding="utf-8") if l.strip()]

    r1_list, r3_list, r5_list, r10_list, p5_list, mrr_list, ndcg10_list = [], [], [], [], [], [], []
    distractor_avoidance_list = []

    category_stats = {}
    records = []

    for idx, c in enumerate(cases, 1):
        cid = c["scenario_id"]
        cat = c.get("category", "GENERAL")
        full_query = (c.get("fact_pattern", "") + "\n\n" + c.get("legal_question", "")).strip()

        pack = retriever.retrieve_evidence_pack(full_query, top_k=10)
        retrieved_secs = pack.get("retrieved_sections", [])

        ret_pairs = []
        for s in retrieved_secs:
            st = s.get("short_name") or ("BNS" if "Nyaya" in s.get("statute","") else ("BNSS" if "Nagarik" in s.get("statute","") else ("BSA" if "Sakshya" in s.get("statute","") else ("POCSO" if "POCSO" in s.get("statute","") else s.get("statute","")))))
            sec = normalize_sec(s.get("section", ""))
            ret_pairs.append((st.upper(), sec))

        exp_pairs = [(e["statute"].upper(), normalize_sec(e["section"])) for e in c.get("expected_sections", [])]
        exp_set = set(exp_pairs)

        distract_pairs = [(d["statute"].upper(), normalize_sec(d["section"])) for d in c.get("distractor_sections", [])]
        distract_set = set(distract_pairs)

        # Recalls
        def calc_recall(sub_pairs):
            if not exp_pairs: return 1.0
            matched = [ep for ep in exp_pairs if ep in sub_pairs or any(ep[0] == rp[0] and ep[1] == rp[1] for rp in sub_pairs)]
            return len(matched) / len(exp_pairs)

        top_1 = ret_pairs[:1]
        top_3 = ret_pairs[:3]
        top_5 = ret_pairs[:5]
        top_10 = ret_pairs[:10]

        rec_1 = calc_recall(top_1)
        rec_3 = calc_recall(top_3)
        rec_5 = calc_recall(top_5)
        rec_10 = calc_recall(top_10)

        # Precision@5
        matched_5 = [rp for rp in top_5 if rp in exp_set or any(rp[0] == ep[0] and rp[1] == ep[1] for ep in exp_set)]
        prec_5 = len(matched_5) / len(top_5) if top_5 else 0.0

        # MRR
        rr = 0.0
        for r_idx, rp in enumerate(ret_pairs, 1):
            if rp in exp_set or any(rp[0] == ep[0] and rp[1] == ep[1] for ep in exp_set):
                rr = 1.0 / r_idx
                break

        # NDCG@10
        ndcg10 = compute_ndcg_at_k(ret_pairs, exp_set, k=10)

        # Distractor Avoidance in Top 5 (1.0 if no distractor appeared in top 5)
        distractor_hits = [rp for rp in top_5 if rp in distract_set or any(rp[0] == dp[0] and rp[1] == dp[1] for dp in distract_set)]
        distractor_avoidance = 1.0 if not distractor_hits else 0.0

        r1_list.append(rec_1)
        r3_list.append(rec_3)
        r5_list.append(rec_5)
        r10_list.append(rec_10)
        p5_list.append(prec_5)
        mrr_list.append(rr)
        ndcg10_list.append(ndcg10)
        distractor_avoidance_list.append(distractor_avoidance)

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "r5": 0.0, "r10": 0.0, "p5": 0.0, "mrr": 0.0, "distract_avoid": 0.0}
        category_stats[cat]["total"] += 1
        category_stats[cat]["r5"] += rec_5
        category_stats[cat]["r10"] += rec_10
        category_stats[cat]["p5"] += prec_5
        category_stats[cat]["mrr"] += rr
        category_stats[cat]["distract_avoid"] += distractor_avoidance

        records.append({
            "scenario_id": cid,
            "category": cat,
            "expected_sections": exp_pairs,
            "distractor_sections": distract_pairs,
            "retrieved_top_5": top_5,
            "retrieved_top_10": top_10,
            "recall@1": round(rec_1, 4),
            "recall@5": round(rec_5, 4),
            "recall@10": round(rec_10, 4),
            "precision@5": round(prec_5, 4),
            "mrr": round(rr, 4),
            "ndcg@10": round(ndcg10, 4),
            "distractor_avoided": distractor_avoidance == 1.0
        })

    n = len(cases)
    avg_r1 = sum(r1_list) / n * 100
    avg_r3 = sum(r3_list) / n * 100
    avg_r5 = sum(r5_list) / n * 100
    avg_r10 = sum(r10_list) / n * 100
    avg_p5 = sum(p5_list) / n * 100
    avg_mrr = sum(mrr_list) / n
    avg_ndcg10 = sum(ndcg10_list) / n
    avg_avoid = sum(distractor_avoidance_list) / n * 100

    out_json = Path("evaluation/phase_8_2i_blind_validation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "Recall@1": round(avg_r1, 2),
                "Recall@3": round(avg_r3, 2),
                "Recall@5": round(avg_r5, 2),
                "Recall@10": round(avg_r10, 2),
                "Precision@5": round(avg_p5, 2),
                "MRR": round(avg_mrr, 4),
                "NDCG@10": round(avg_ndcg10, 4),
                "Distractor_Avoidance_Rate": round(avg_avoid, 2)
            },
            "category_breakdown": {
                k: {
                    "total_cases": v["total"],
                    "Recall@5": round(v["r5"] / v["total"] * 100, 2),
                    "Recall@10": round(v["r10"] / v["total"] * 100, 2),
                    "Precision@5": round(v["p5"] / v["total"] * 100, 2),
                    "MRR": round(v["mrr"] / v["total"], 4),
                    "Distractor_Avoidance": round(v["distract_avoid"] / v["total"] * 100, 2)
                } for k, v in category_stats.items()
            },
            "records": records
        }, f, indent=2, ensure_ascii=False)

    print(f"=== 100-SCENARIO BLIND VALIDATION RESULTS ===")
    print(f"• Recall@1:                  {avg_r1:.2f}%")
    print(f"• Recall@3:                  {avg_r3:.2f}%")
    print(f"• Recall@5:                  {avg_r5:.2f}%")
    print(f"• Recall@10:                 {avg_r10:.2f}%")
    print(f"• Precision@5:               {avg_p5:.2f}%")
    print(f"• MRR:                       {avg_mrr:.4f}")
    print(f"• NDCG@10:                   {avg_ndcg10:.4f}")
    print(f"• Distractor Avoidance Rate: {avg_avoid:.2f}%\n")

    print("=== CATEGORY-LEVEL ACCURACY ===")
    for k, v in category_stats.items():
        tot = v["total"]
        r5 = v["r5"] / tot * 100
        r10 = v["r10"] / tot * 100
        p5 = v["p5"] / tot * 100
        m = v["mrr"] / tot
        da = v["distract_avoid"] / tot * 100
        print(f"{k:25s}: Total={tot:3d} | R@5={r5:5.2f}% | R@10={r10:5.2f}% | P@5={p5:5.2f}% | MRR={m:.4f} | DistrAvoid={da:5.2f}%")

if __name__ == "__main__":
    run_blind_validation()
