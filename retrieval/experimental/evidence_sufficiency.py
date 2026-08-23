# evidence_sufficiency.py — Evidence Grounding & Sufficiency Evaluator (Phase 8.2G Experimental)
#
# Objective:
# Evaluate whether retrieved statutory sections provide sufficient legal authority to support
# conclusions on each identified legal issue, without inventing law or hallucinating unsupported rules.

import re
from typing import Dict, List, Any, Set, Tuple

class EvidenceSufficiencyEvaluator:
    """Evaluates evidence sufficiency across decomposed legal issues."""

    def __init__(self):
        pass

    def evaluate_sufficiency(self, issues: List[Dict[str, Any]], reranked_evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check whether each legal issue is supported by retrieved sections."""
        evaluations = []
        overall_supported_count = 0
        
        # Build index of retrieved sections by statute
        retrieved_by_statute = {}
        for item in reranked_evidence:
            st = item.get("statute", "").upper()
            if st not in retrieved_by_statute:
                retrieved_by_statute[st] = []
            retrieved_by_statute[st].append(f"{st} Section {item.get('section')}")

        for iss in issues:
            issue_type = iss.get("issue_type")
            candidate_statutes = iss.get("statute_candidates", [])
            matched_concepts = iss.get("matched_concepts", [])

            # Find supporting sections from target candidate statutes
            supporting = []
            for st in candidate_statutes:
                if st in retrieved_by_statute:
                    supporting.extend(retrieved_by_statute[st])

            if len(supporting) >= 2:
                status = "SUPPORTED"
                reason = f"Comprehensive statutory authority found in {list(candidate_statutes)}: {', '.join(supporting[:3])}."
                overall_supported_count += 1
            elif len(supporting) == 1:
                status = "PARTIALLY_SUPPORTED"
                reason = f"Single statutory section found: {supporting[0]}. Additional corroborating authority recommended."
                overall_supported_count += 1
            else:
                status = "INSUFFICIENT_EVIDENCE"
                reason = f"No primary statutory evidence retrieved for candidate statutes {list(candidate_statutes)}. Legal conclusion must be qualified."

            evaluations.append({
                "issue": issue_type,
                "status": status,
                "supporting_sections": supporting,
                "reason": reason
            })

        all_supported = (overall_supported_count == len(issues)) and (len(issues) > 0)
        overall_status = "FULLY_SUPPORTED" if all_supported else ("PARTIALLY_SUPPORTED" if overall_supported_count > 0 else "INSUFFICIENT_EVIDENCE")

        return {
            "overall_status": overall_status,
            "supported_issue_count": overall_supported_count,
            "total_issue_count": len(issues),
            "sufficiency_ratio": round(overall_supported_count / len(issues), 2) if issues else 0.0,
            "issue_evaluations": evaluations
        }
