import json
import sys
from pathlib import Path

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from experimental_phase_8_2g.pipeline import ExperimentalLegalPipeline

adv_raw = {c["scenario_id"]: c for c in [json.loads(l) for l in open(r"C:\Users\joyde\Downloads\nyaya_darshana_50_advanced_hybrid_cases.jsonl", encoding="utf-8") if l.strip()]}
adv_gt = json.load(open("evaluation/ground_truth_adv_50.json", encoding="utf-8"))

for cid in ["ADV-002", "ADV-014", "ADV-037"]:
    raw = adv_raw[cid]
    gt = adv_gt[cid]
    q = (raw.get("fact_pattern", "") + " " + raw.get("legal_question", "")).strip()
    print(f"==================== {cid} ====================")
    print("Expected Sections:", gt.get("expected_sections"))
    print("Acceptable Alt Sections:", gt.get("acceptable_alternative_sections"))
    
    br = AuthoritativeLegalRetriever()
    ep_base = br.retrieve_evidence_pack(q, top_k=6)
    base_secs = [(s.get("short_name"), s.get("section")) for s in ep_base.get("retrieved_sections", [])]
    print("Baseline Retrieved (Top 6):", base_secs)
    
    pipeline = ExperimentalLegalPipeline()
    res_exp = pipeline.process_query(q)
    exp_secs = [(s.get("statute"), s.get("section")) for s in res_exp.get("retrieved_sections", [])]
    print("Experimental Retrieved (Top 8):", exp_secs)
    print()
