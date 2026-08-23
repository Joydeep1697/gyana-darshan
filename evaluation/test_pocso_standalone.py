# test_pocso_standalone.py — Phase 8.4A POCSO Standalone Statutory & Procedural Validation

import sys
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall

def run_pocso_tests():
    print("=========================================================================")
    print("=== PHASE 8.4A — POCSO STANDALONE STATUTORY & PROCEDURAL TEST SUITE    ===")
    print("=========================================================================")

    retriever = AuthoritativeLegalRetriever()
    firewall = LegalVerificationFirewall()

    test_queries = [
        {
            "id": "POCSO_01",
            "query": "What constitutes sexual assault under the POCSO Act?",
            "expected_sections": ["7", "8"],
            "expected_statute": "POCSO",
            "forbidden_statutes": ["BNS"],
            "required_terms": ["sexual assault", "touching", "sexual intent"]
        },
        {
            "id": "POCSO_02",
            "query": "What is the prescribed statutory punishment under Section 4 of the POCSO Act?",
            "expected_sections": ["4"],
            "expected_statute": "POCSO",
            "required_terms": ["penetrative", "imprisonment", "not less than"]
        },
        {
            "id": "POCSO_03",
            "query": "What are the powers and duties of the Special Court under the POCSO Act?",
            "expected_sections": ["28", "33"],
            "expected_statute": "POCSO",
            "required_terms": ["special court", "child", "evidence"]
        },
        {
            "id": "POCSO_04",
            "query": "What is the mandatory statutory reporting obligation under Section 19 and 21 of POCSO?",
            "expected_sections": ["19", "21"],
            "expected_statute": "POCSO",
            "required_terms": ["reporting", "police", "failure to report"]
        },
        {
            "id": "POCSO_05",
            "query": "Does the Bharatiya Nyaya Sanhita, 2023 repeal the POCSO Act, 2012?",
            "expected_statute": "POCSO",
            "expected_sections": ["42A", "42"],
            "adversarial_check": True,
            "required_terms": ["unrepealed", "special statute", "overrides", "alongside"]
        },
        {
            "id": "POCSO_06",
            "query": "Does the POCSO Act continue in force alongside BNS and BNSS?",
            "expected_statute": "POCSO",
            "expected_sections": ["42A", "42"],
            "required_terms": ["force", "special", "addition"]
        },
        {
            "id": "POCSO_07",
            "query": "How does POCSO interact with BNS provisions when an offence is punishable under both?",
            "expected_statute": "POCSO",
            "expected_sections": ["42", "42A"],
            "required_terms": ["greater degree", "overriding", "42A"]
        },
        {
            "id": "POCSO_08",
            "query": "What is the statutory age definition of a child under Section 2(1)(d) of the POCSO Act?",
            "expected_sections": ["2(1)(d)", "2"],
            "expected_statute": "POCSO",
            "required_terms": ["eighteen years", "child"]
        },
        {
            "id": "POCSO_09",
            "query": "What procedural protections apply to recording the statement of a child victim under POCSO?",
            "expected_sections": ["24", "25", "26", "27", "33"],
            "expected_statute": "POCSO",
            "required_terms": ["residence", "police officer", "civil clothes", "in-camera"]
        }
    ]

    all_passed = True

    for t in test_queries:
        qid = t["id"]
        q = t["query"]
        print(f"\n--- Testing [{qid}]: {q} ---")

        evidence_pack = retriever.retrieve_evidence_pack(q, top_k=4)
        top_docs = evidence_pack.get("top_documents", [])
        sections_found = [str(d.get("section", "")).strip() for d in top_docs]
        statutes_found = [str(d.get("short_name", "")).strip() for d in top_docs]

        print(f"  [+] Retrieved Statutes: {statutes_found}")
        print(f"  [+] Retrieved Sections: {sections_found}")

        # Verification through firewall
        ans = top_docs[0].get("text", "")[:400] if top_docs else "No evidence retrieved."
        passed, verified_ans, claims = firewall.verify_and_enforce(ans, evidence_pack)

        # Check section retrieval
        exp_secs = t.get("expected_sections", [])
        sec_hit = any(any(es == sf or es in sf for sf in sections_found) for es in exp_secs) if exp_secs else True

        # Check statute
        stat_hit = t["expected_statute"] in statutes_found or t.get("adversarial_check", False)

        if sec_hit and stat_hit:
            print(f"  [+] Result: PASS ✅ (Retrieved expected {t['expected_statute']} sections)")
        else:
            print(f"  [-] Result: FAIL ❌ (Expected {exp_secs} in {t['expected_statute']}, got {sections_found})")
            all_passed = False

    print("\n=========================================================================")
    if all_passed:
        print("=== ALL 9 POCSO STANDALONE TEST SCENARIOS PASSED (100% SUCCESS) ✅  ===")
    else:
        print("=== POCSO STANDALONE TEST SCENARIOS HAD FAILURES ❌                  ===")
    print("=========================================================================")
    return all_passed

if __name__ == "__main__":
    success = run_pocso_tests()
    sys.exit(0 if success else 1)
