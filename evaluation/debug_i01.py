import sys, json
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from evaluation.run_phase_8_2b_novel_scenario_benchmark import evaluate_answer_correctness

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

records = [json.loads(l) for l in open("d:/Nova Legal/evaluation/phase_8_2b_novel_scenario_benchmark.jsonl", encoding="utf-8") if l.strip()]
rec_i01 = [rec for rec in records if rec["scenario_id"] == "I01"][0]

query = rec_i01["fact_pattern"] + " " + rec_i01["legal_question"]
ep = r.retrieve_evidence_pack(query)
raw_ans = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep)}\nIn response to '{query}', the position is established under statute."
passed_fw, final_ans, claims = fw.verify_and_enforce(raw_ans, ep)

print("Query:", query)
print("Passed FW:", passed_fw)
print("Final Ans:", final_ans)
print("Expected Statutes:", rec_i01["expected_statutes"])
print("Expected Sec:", rec_i01["expected_sections"])
print("Expected Prop:", rec_i01["expected_legal_proposition"])
print("Prohib:", rec_i01["prohibited_false_propositions"])

print("Eval Final:", evaluate_answer_correctness(final_ans, rec_i01["expected_statutes"], rec_i01["expected_sections"], rec_i01["expected_legal_proposition"], rec_i01["prohibited_false_propositions"]))
