import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from evaluation.run_phase_8_2b_novel_scenario_benchmark import evaluate_answer_correctness

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

q_g01 = "A police investigation involves an alleged BNS offence, an arrest, and a seized smartphone containing relevant messages. Which statutes should be separated by legal function?"
ep = r.retrieve_evidence_pack(q_g01)
raw_ans = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep)}\nIn response to '{q_g01}', the legal analysis confirms the statutory position."
p, ans, c = fw.verify_and_enforce(raw_ans, ep)

print("=== G01 EVAL DEBUG ===")
print("Candidate Statutes:", ep["query_analysis"]["candidate_statutes"])
print("Retrieved Sections:", [(s["short_name"], s["section"]) for s in ep["retrieved_sections"]])
print("Answer Text:\n", ans[:400])

eval_res = evaluate_answer_correctness(
    ans,
    ["BNS", "BNSS", "BSA"],
    ["Relevant BNS offence; BNSS arrest/seizure; BSA electronic evidence"],
    "BNS governs substantive offences, BNSS criminal procedure, and BSA evidence; the answer should retrieve each layer separately.",
    "Single statute governs all three; BNS governs procedure"
)
print("Eval Result:", eval_res)
