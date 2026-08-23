"""transition_router.py — Dedicated Transition and Savings Law Router for Nyaya Darshana.

Classifies queries dealing with:
1. Pre-1 July 2024 vs Post-1 July 2024 offences and investigations
2. Pending trials and proceedings under CrPC 1973 vs BNSS 2023
3. Repeal and savings clauses (BNS Section 358, BNSS Section 531, BSA Section 170)
4. Constitutional protections under Article 20(1) and General Clauses Act Section 6
"""

from typing import Dict, Any, Optional, List
import re

class TransitionLawRouter:
    """Detects and routes transitional statutory questions to authoritative repeal and savings provisions."""

    TRANSITION_KEYWORDS = [
        "transition", "repeal and saving", "repeal and savings", "saving clause", "savings clause",
        "pending investigation", "pending trial", "pending proceeding", "pending appeal",
        "before 1 july 2024", "prior to 1 july 2024", "after 1 july 2024", "on or after 1 july 2024",
        "retrospective", "prospective", "article 20(1)", "general clauses act",
        "charge-sheet filed after", "fir before 1 july", "offence committed before",
        "old law or new law", "old act or new act", "convert ipc", "convert crpc", "convert iea",
        "substitute bns throughout", "substitute bnss throughout", "substitute bsa throughout"
    ]

    def is_transition_query(self, query: str) -> bool:
        """Determine if a query raises statutory transition or savings issues."""
        q_lower = query.lower()
        
        # Check explicit transition terms
        if any(kw in q_lower for kw in self.TRANSITION_KEYWORDS):
            return True
        
        # Check cross-statutory combination mentions
        has_old = any(w in q_lower for w in ["ipc", "crpc", "iea", "indian penal code", "code of criminal procedure", "indian evidence act"])
        has_new = any(w in q_lower for w in ["bns", "bnss", "bsa", "bharatiya nyaya", "bharatiya nagarik", "bharatiya sakshya"])
        has_timing = any(w in q_lower for w in ["date of offence", "date of fir", "date of enactment", "commencement date", "applicable law", "which statute applies"])
        
        if has_old and has_new and has_timing:
            return True
            
        return False

    def route_transition_evidence(self, query: str) -> Dict[str, Any]:
        """Extract authoritative transition provisions based on the specific transition aspect."""
        q_lower = query.lower()

        candidate_sections: List[Dict[str, str]] = []

        # 1. Substantive Offence Transition (BNS Sec 358)
        if any(w in q_lower for w in ["ipc", "penal code", "offence committed before", "substantive", "bns 358"]):
            candidate_sections.append({
                "statute": "BNS",
                "section": "358",
                "reason": "BNS Section 358 (Repeal and savings): Offences committed prior to 1 July 2024 are prosecuted under IPC 1860."
            })

        # 2. Procedural Transition & Pending Proceedings (BNSS Sec 531)
        if any(w in q_lower for w in ["crpc", "procedure", "remand", "bail", "investigation", "trial", "appeal", "bnss 531"]):
            candidate_sections.append({
                "statute": "BNSS",
                "section": "531",
                "reason": "BNSS Section 531(2)(a) (Repeal and savings): Pending investigations, inquiries, trials, and appeals instituted prior to 1 July 2024 continue under CrPC 1973."
            })

        # 3. Evidence Transition (BSA Sec 170)
        if any(w in q_lower for w in ["iea", "evidence", "ruling", "admissibility", "electronic record", "bsa 170"]):
            candidate_sections.append({
                "statute": "BSA",
                "section": "170",
                "reason": "BSA Section 170 (Repeal and savings): Application to evidence tendered in proceedings."
            })

        # Default fallback: provide both BNS 358 and BNSS 531
        if not candidate_sections:
            candidate_sections = [
                {"statute": "BNS", "section": "358", "reason": "BNS Section 358 Repeal and Savings"},
                {"statute": "BNSS", "section": "531", "reason": "BNSS Section 531 Repeal and Savings"}
            ]

        return {
            "is_transition": True,
            "statutory_principle": "Substantive penal liability is governed strictly by the law in force on the date of commission (Art. 20(1) Constitution & Sec. 6 General Clauses Act 1897). Procedural law under BNSS applies to new proceedings instituted on or after 1 July 2024, while pending proceedings continue under CrPC per BNSS Sec. 531(2)(a).",
            "candidate_sections": candidate_sections
        }
