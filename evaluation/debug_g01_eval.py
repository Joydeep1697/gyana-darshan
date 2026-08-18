import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from evaluation.run_phase_8_2b_novel_scenario_benchmark import evaluate_answer_correctness, extract_section_tokens

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

q_g01 = "A police investigation involves an alleged BNS offence, an arrest, and a seized smartphone containing relevant messages. Which statutes should be separated by legal function?"
ep = r.retrieve_evidence_pack(q_g01)
raw_ans = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep)}\nIn response to '{q_g01}', the legal analysis confirms the statutory position."
p, ans, c = fw.verify_and_enforce(raw_ans, ep)

expected_statutes = ["BNS", "BNSS", "BSA"]
expected_sections = ["Relevant BNS offence; BNSS arrest/seizure; BSA electronic evidence"]
expected_prop = "BNS governs substantive offences, BNSS criminal procedure, and BSA evidence; the answer should retrieve each layer separately."
prohib_str = "Single statute governs all three; BNS governs procedure"

ans_lower = ans.lower()
print("1. All statutes in ans:", all(st.lower() in ans_lower or ("bharatiya nyaya" in ans_lower if st == "BNS" else ("bharatiya nagarik" in ans_lower if st == "BNSS" else ("bharatiya sakshya" in ans_lower if st == "BSA" else False))) for st in expected_statutes))
print("2. Section check details:")
tokens = extract_section_tokens(ans)
print("Tokens:", tokens)
for sec in expected_sections:
    print(f"Sec '{sec}' in ans:", sec in ans)
