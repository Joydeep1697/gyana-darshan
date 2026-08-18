# test_mandatory_regressions.py — Verify the 7 Mandatory Regression Tests for Phase 8.2A

import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall

def run_regression_tests():
    p = ProceduralRulesRegistry()
    r = AuthoritativeLegalRetriever()
    fw = LegalVerificationFirewall()

    print("=========================================================================")
    print("=== PHASE 8.2A — MANDATORY REGRESSION TEST SUITE                      ===")
    print("=========================================================================")

    all_passed = True

    # 1. Which Act replaced the Indian Evidence Act, 1872?
    q1 = "Which Act replaced the Indian Evidence Act, 1872?"
    ep1 = r.retrieve_evidence_pack(q1)
    passed1, ans1, _ = fw.verify_and_enforce(r.format_evidence_context(ep1), ep1)
    rule1 = p.lookup_procedural_rule(q1)
    pass1 = (rule1 is None) and ("bharatiya sakshya adhiniyam" in ans1.lower() or "bsa" in ans1.lower()) and ("187" not in ans1 or "1872" in ans1)
    print(f"\n1. {q1}")
    print(f"   Procedural Rule 187 Falsely Triggered: {rule1 is not None} (Expected: False)")
    print(f"   Answer: {ans1[:100]}...")
    print(f"   Status: {'PASS ✅' if pass1 else 'FAIL ❌'}")
    if not pass1: all_passed = False

    # 2. Which Act replaced the Indian Evidence Act?
    q2 = "Which Act replaced the Indian Evidence Act?"
    ep2 = r.retrieve_evidence_pack(q2)
    passed2, ans2, _ = fw.verify_and_enforce(r.format_evidence_context(ep2), ep2)
    pass2 = "bharatiya sakshya adhiniyam" in ans2.lower() or "bsa" in ans2.lower()
    print(f"\n2. {q2}")
    print(f"   Answer: {ans2[:100]}...")
    print(f"   Status: {'PASS ✅' if pass2 else 'FAIL ❌'}")
    if not pass2: all_passed = False

    # 3. Which section deals with police custody under BNSS?
    q3 = "Which section deals with police custody under BNSS?"
    ep3 = r.retrieve_evidence_pack(q3)
    passed3, ans3, _ = fw.verify_and_enforce(r.format_evidence_context(ep3), ep3)
    rule3 = p.lookup_procedural_rule(q3)
    pass3 = rule3 is not None and "187" in ans3
    print(f"\n3. {q3}")
    print(f"   Rule Matched: {rule3['section'] if rule3 else None}")
    print(f"   Answer: {ans3[:100]}...")
    print(f"   Status: {'PASS ✅' if pass3 else 'FAIL ❌'}")
    if not pass3: all_passed = False

    # 4. Explain BNSS Section 187.
    q4 = "Explain BNSS Section 187."
    ep4 = r.retrieve_evidence_pack(q4)
    passed4, ans4, _ = fw.verify_and_enforce(r.format_evidence_context(ep4), ep4)
    rule4 = p.lookup_procedural_rule(q4)
    pass4 = rule4 is not None and "187" in ans4
    print(f"\n4. {q4}")
    print(f"   Rule Matched: {rule4['section'] if rule4 else None}")
    print(f"   Answer: {ans4[:100]}...")
    print(f"   Status: {'PASS ✅' if pass4 else 'FAIL ❌'}")
    if not pass4: all_passed = False

    # 5. What is the equivalent of CrPC Section 167?
    q5 = "What is the equivalent of CrPC Section 167?"
    ep5 = r.retrieve_evidence_pack(q5)
    passed5, ans5, _ = fw.verify_and_enforce(r.format_evidence_context(ep5), ep5)
    pass5 = "187" in ans5 and "bharatiya nagarik suraksha sanhita" in ans5.lower()
    print(f"\n5. {q5}")
    print(f"   Answer: {ans5[:100]}...")
    print(f"   Status: {'PASS ✅' if pass5 else 'FAIL ❌'}")
    if not pass5: all_passed = False

    # 6. What happened in 1872?
    q6 = "What happened in 1872?"
    rule6 = p.lookup_procedural_rule(q6)
    pass6 = rule6 is None
    print(f"\n6. {q6}")
    print(f"   Procedural Rule Falsely Matched: {rule6 is not None} (Expected: False)")
    print(f"   Status: {'PASS ✅' if pass6 else 'FAIL ❌'}")
    if not pass6: all_passed = False

    # 7. Which Act was enacted in 1872?
    q7 = "Which Act was enacted in 1872?"
    rule7 = p.lookup_procedural_rule(q7)
    pass7 = rule7 is None
    print(f"\n7. {q7}")
    print(f"   Procedural Rule Falsely Matched: {rule7 is not None} (Expected: False)")
    print(f"   Status: {'PASS ✅' if pass7 else 'FAIL ❌'}")
    if not pass7: all_passed = False

    print("\n=========================================================================")
    print(f"=== ALL MANDATORY REGRESSION TESTS: {'ALL 7 PASSED ✅' if all_passed else 'FAILED ❌'}               ===")
    print("=========================================================================")
    return all_passed

if __name__ == "__main__":
    success = run_regression_tests()
    sys.exit(0 if success else 1)
