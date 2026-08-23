# verify_phase_8_2c_fixes.py

import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from evaluation.run_phase_8_2b_novel_scenario_benchmark import evaluate_answer_correctness

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

# 1. Test A05
q_a05 = "A person secretly takes another person's movable property without consent and with dishonest intention. Which BNS provision addresses theft?"
ep_a05 = r.retrieve_evidence_pack(q_a05)
raw_a05 = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep_a05)}\nIn response to '{q_a05}', the authoritative legal position is established under statute."
p_a05, ans_a05, c_a05 = fw.verify_and_enforce(raw_a05, ep_a05)
eval_a05 = evaluate_answer_correctness(ans_a05, ["BNS"], ["303"], "BNS section 303 addresses theft.", "BNS section 379; BNSS section 303")
print("=== A05 VERIFICATION ===")
print("Passed FW:", p_a05)
print("Sections in ep:", [s["section"] for s in ep_a05["retrieved_sections"]])
print("Statutes in ep:", [s["short_name"] for s in ep_a05["retrieved_sections"]])
print("Answer Snippet:\n", ans_a05[:300])
print("A05 Eval Correctness:", eval_a05)
