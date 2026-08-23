import sys, json
from pathlib import Path
BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from evaluation.run_phase_8_2b_novel_scenario_benchmark import evaluate_answer_correctness, evaluate_retrieval_pack, check_prohibited_claims

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

records = [json.loads(l) for l in open("d:/Gyana Darshan/evaluation/phase_8_2b_novel_scenario_benchmark.jsonl", encoding="utf-8") if l.strip()]
rec_j03 = [rec for rec in records if rec["scenario_id"] == "J03"][0]

query = rec_j03["fact_pattern"] + " " + rec_j03["legal_question"]
ep = r.retrieve_evidence_pack(query)
raw_ans = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep)}\nIn response to '{query}', the position is established under statute."
passed_fw, final_ans, claims = fw.verify_and_enforce(raw_ans, ep)

ret_eval = evaluate_retrieval_pack(rec_j03["expected_statutes"], rec_j03["expected_sections"], ep)
raw_pass = evaluate_answer_correctness(raw_ans, rec_j03["expected_statutes"], rec_j03["expected_sections"], rec_j03["expected_legal_proposition"], rec_j03["prohibited_false_propositions"])
final_pass = evaluate_answer_correctness(final_ans, rec_j03["expected_statutes"], rec_j03["expected_sections"], rec_j03["expected_legal_proposition"], rec_j03["prohibited_false_propositions"])

print("Query:", query)
print("Passed FW:", passed_fw)
print("Final Ans:", final_ans)
print("Raw Pass:", raw_pass)
print("Final Pass:", final_pass)
print("Ret Eval:", ret_eval)
