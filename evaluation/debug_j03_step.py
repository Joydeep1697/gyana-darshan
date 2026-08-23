import sys, json, re
from pathlib import Path
BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from evaluation.run_phase_8_2b_novel_scenario_benchmark import extract_section_tokens, check_prohibited_claims

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

records = [json.loads(l) for l in open("d:/Gyana Darshan/evaluation/phase_8_2b_novel_scenario_benchmark.jsonl", encoding="utf-8") if l.strip()]
rec_j03 = [rec for rec in records if rec["scenario_id"] == "J03"][0]

query = rec_j03["fact_pattern"] + " " + rec_j03["legal_question"]
ep = r.retrieve_evidence_pack(query)
raw_ans = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep)}\nIn response to '{query}', the position is established under statute."
passed_fw, final_ans, claims = fw.verify_and_enforce(raw_ans, ep)

def debug_eval(answer, expected_statutes, expected_sections, expected_prop, prohibited_str):
    has_false_claim, viols = check_prohibited_claims(answer, prohibited_str)
    print("False claim:", has_false_claim, viols)
    if has_false_claim: return False

    ans_lower = answer.lower()
    
    if "false" in expected_prop.lower() or "not" in expected_prop.lower():
        if "false" in ans_lower or "does not" in ans_lower or "cannot" in ans_lower or "unrepealed" in ans_lower:
            print("Adversarial check pass")
            return True

    statute_ok = False
    for st in expected_statutes:
        st_l = st.lower()
        if st_l == "bns" and ("bns" in ans_lower or "bharatiya nyaya" in ans_lower):
            statute_ok = True
        elif st_l == "bnss" and ("bnss" in ans_lower or "bharatiya nagarik" in ans_lower):
            statute_ok = True
        elif st_l == "bsa" and ("bsa" in ans_lower or "bharatiya sakshya" in ans_lower):
            statute_ok = True
        elif st_l == "pocso" and "pocso" in ans_lower:
            statute_ok = True
        elif st_l in ans_lower:
            statute_ok = True
    print("Statute ok:", statute_ok)

    if not statute_ok and expected_statutes:
        return False

    if expected_sections:
        sec_ok = False
        ans_tokens = extract_section_tokens(answer)
        print("Ans tokens:", ans_tokens)
        for sec in expected_sections:
            sec_clean = str(sec).strip()
            sec_base = re.sub(r'\(.*?\)', '', sec_clean).strip()
            print(f"Checking sec '{sec_clean}', base '{sec_base}': in ans={sec_clean in answer}, in tokens={sec_base in ans_tokens}")
            if sec_clean in answer or sec_base in ans_tokens or sec_clean.lower() in ans_lower:
                sec_ok = True
                break
        print("Sec ok:", sec_ok)
        if not sec_ok:
            return False

    return True

print("Evaluating Final Ans:")
res = debug_eval(final_ans, rec_j03["expected_statutes"], rec_j03["expected_sections"], rec_j03["expected_legal_proposition"], rec_j03["prohibited_false_propositions"])
print("Result:", res)
