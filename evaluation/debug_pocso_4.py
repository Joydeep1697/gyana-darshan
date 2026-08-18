import sys
from pathlib import Path
sys.path.append(r"d:\Nova Legal")
import json
from retrieval.query_analyzer import LegalQueryAnalyzer
from retrieval.hybrid_retriever import AuthoritativeLegalRetriever

q_analyzer = LegalQueryAnalyzer()
retriever = AuthoritativeLegalRetriever()

bench = [json.loads(l) for l in open("d:/Nova Legal/evaluation/phase_8_2d_stress_benchmark.jsonl", encoding="utf-8") if l.strip()]

for sid in ["ND_POCSO_11", "ND_POCSO_16", "ND_POCSO_19", "ND_POCSO_20"]:
    rec = [x for x in bench if x["scenario_id"] == sid][0]
    query = rec["fact_pattern"] + " " + rec["legal_question"]
    analysis = q_analyzer.analyze_query(query)
    ep = retriever.retrieve_evidence_pack(query)
    print(f"=== {sid} ===")
    print("Query:", query[:90])
    print("Matched concepts:", analysis["matched_concepts"])
    print("Candidate statutes:", analysis["candidate_statutes"])
    print("Candidate sections:", analysis["candidate_sections"])
    print("Retrieved sections:", [s.get("section") for s in ep.get("retrieved_sections", [])])
