"""run_phase_8_2j_ablation_study.py — Phase 8.2J Multi-Configuration Ablation Study.

Compares:
1. Config A: Phase 8.2I Baseline (MRR 0.8178, R@5 61.53%, R@10 68.25%, P@5 34.60%)
2. Config B: Global Top-K Expansion (top_k=20 unconstrained)
3. Config C: Issue-Aware Candidate Budget (Phase 8.2J)
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

def evaluate_retriever_config(config_name: str, top_k_param: int):
    retriever = AuthoritativeLegalRetriever()
    ground_truth = json.load(open("evaluation/phase_8_2g_ground_truth_audit.json", encoding="utf-8"))
    
    # Load raw cases
    adv_cases = json.load(open("evaluation/ground_truth_adv_50_verified.json", encoding="utf-8"))
    blind_cases = [json.loads(l) for l in open("evaluation/narrative_blind_50_verified.jsonl", encoding="utf-8") if l.strip()]
    raw_map = dict(adv_cases)
    for c in blind_cases:
        raw_map[c["scenario_id"]] = c

    r1_list, r3_list, r5_list, r10_list, p5_list, mrr_list, ndcg10_list = [], [], [], [], [], [], []

    for item in ground_truth:
        cid = item["case_id"]
        raw_case = raw_map.get(cid, {})
        full_query = (raw_case.get("fact_pattern", "") + "\n\n" + raw_case.get("legal_question", "")).strip() or item.get("scenario", "")
        
        exp_secs_raw = item.get("independently_verified_sections", []) or item.get("existing_expected_sections", [])
        exp_pairs = [(e["statute"].upper(), normalize_sec(e["section"])) for e in exp_secs_raw]
        exp_set = set(exp_pairs)

        pack = retriever.retrieve_evidence_pack(full_query, top_k=top_k_param)
        retrieved_secs = pack.get("retrieved_sections", [])

        ret_pairs = []
        for s in retrieved_secs:
            st = s.get("short_name") or ("BNS" if "Nyaya" in s.get("statute","") else ("BNSS" if "Nagarik" in s.get("statute","") else ("BSA" if "Sakshya" in s.get("statute","") else ("POCSO" if "POCSO" in s.get("statute","") else s.get("statute","")))))
            sec = normalize_sec(s.get("section", ""))
            ret_pairs.append((st.upper(), sec))

        def calc_recall(sub_pairs):
            if not exp_pairs: return 1.0
            matched = [ep for ep in exp_pairs if ep in sub_pairs or any(ep[0] == rp[0] and ep[1] == rp[1] for rp in sub_pairs)]
            return len(matched) / len(exp_pairs)

        r1 = calc_recall(ret_pairs[:1])
        r3 = calc_recall(ret_pairs[:3])
        r5 = calc_recall(ret_pairs[:5])
        r10 = calc_recall(ret_pairs[:10])

        matched_5 = [rp for rp in ret_pairs[:5] if rp in exp_set or any(rp[0] == ep[0] and rp[1] == ep[1] for ep in exp_set)]
        p5 = len(matched_5) / len(ret_pairs[:5]) if ret_pairs[:5] else 0.0

        rr = 0.0
        for r_idx, rp in enumerate(ret_pairs, 1):
            if rp in exp_set or any(rp[0] == ep[0] and rp[1] == ep[1] for ep in exp_set):
                rr = 1.0 / r_idx
                break

        ndcg10 = compute_ndcg_at_k(ret_pairs, exp_set, k=10)

        r1_list.append(r1)
        r3_list.append(r3)
        r5_list.append(r5)
        r10_list.append(r10)
        p5_list.append(p5)
        mrr_list.append(rr)
        ndcg10_list.append(ndcg10)

    n = len(ground_truth)
    res = {
        "config": config_name,
        "Recall@1": round(sum(r1_list) / n * 100, 2),
        "Recall@3": round(sum(r3_list) / n * 100, 2),
        "Recall@5": round(sum(r5_list) / n * 100, 2),
        "Recall@10": round(sum(r10_list) / n * 100, 2),
        "Precision@5": round(sum(p5_list) / n * 100, 2),
        "MRR": round(sum(mrr_list) / n, 4),
        "NDCG@10": round(sum(ndcg10_list) / n, 4)
    }
    return res

def run_ablation():
    print("==================================================================")
    print("=== PHASE 8.2J — MULTI-CONFIGURATION ABLATION STUDY            ===")
    print("==================================================================\n")

    res_c = evaluate_retriever_config("Config C: Issue-Aware Candidate Budget (Phase 8.2J)", top_k_param=10)
    res_b = evaluate_retriever_config("Config B: Global Top-K Expansion (Unconstrained top_k=20)", top_k_param=20)
    res_a = {
        "config": "Config A: Phase 8.2I Baseline",
        "Recall@1": 28.51,
        "Recall@3": 53.48,
        "Recall@5": 61.53,
        "Recall@10": 68.25,
        "Precision@5": 34.60,
        "MRR": 0.8178,
        "NDCG@10": 0.6624
    }

    out_json = Path("evaluation/phase_8_2j_ablation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "config_a_baseline_82i": res_a,
            "config_b_global_expansion": res_b,
            "config_c_issue_aware_budget_82j": res_c
        }, f, indent=2, ensure_ascii=False)

    print(f"{'Metric':<25s} | {'Config A (8.2I)':<18s} | {'Config B (Exp-20)':<18s} | {'Config C (8.2J Budget)':<22s}")
    print("-" * 90)
    for m in ["Recall@1", "Recall@3", "Recall@5", "Recall@10", "Precision@5", "MRR", "NDCG@10"]:
        va = f"{res_a[m]}%" if "Recall" in m or "Precision" in m else f"{res_a[m]:.4f}"
        vb = f"{res_b[m]}%" if "Recall" in m or "Precision" in m else f"{res_b[m]:.4f}"
        vc = f"{res_c[m]}%" if "Recall" in m or "Precision" in m else f"{res_c[m]:.4f}"
        print(f"{m:<25s} | {va:<18s} | {vb:<18s} | {vc:<22s}")

if __name__ == "__main__":
    run_ablation()
