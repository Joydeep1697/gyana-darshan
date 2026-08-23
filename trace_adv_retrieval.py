import json
import sys
from pathlib import Path

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from retrieval.experimental.parallel_statute_retriever import ParallelStatuteRetriever

adv_raw = {c["scenario_id"]: c for c in [json.loads(l) for l in open(r"C:\Users\joyde\Downloads\nyaya_darshana_50_advanced_hybrid_cases.jsonl", encoding="utf-8") if l.strip()]}
adv_gt = json.load(open("evaluation/ground_truth_adv_50.json", encoding="utf-8"))

for cid in ["ADV-013", "ADV-016", "ADV-017", "ADV-020"]:
    raw = adv_raw[cid]
    gt = adv_gt[cid]
    q = (raw.get("fact_pattern", "") + " " + raw.get("legal_question", "")).strip()
    print(f"==================== {cid} ====================")
    print("Expected Sections:", gt.get("expected_sections"))
    
    br = AuthoritativeLegalRetriever()
    ep_base = br.retrieve_evidence_pack(q, top_k=6)
    base_secs = [(s.get("short_name"), s.get("section")) for s in ep_base.get("retrieved_sections", [])]
    print("Baseline Retrieved:", base_secs)
    
    pr = ParallelStatuteRetriever()
    ep_exp = pr.retrieve_parallel_branches(q, per_statute_k=3)
    exp_secs = [(s.get("statute"), s.get("section")) for s in ep_exp.get("candidates", [])]
    print("Parallel Retrieved Candidates:", exp_secs)
    print("Active Statutes in Parallel:", ep_exp.get("active_statutes"))
    print("Decomposed Issues:", [iss['issue_type'] for iss in ep_exp['decomposition']['issues']])
    print()
