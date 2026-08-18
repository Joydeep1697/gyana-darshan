# procedural_claim_validator.py — Nyaya Legal OS Phase 6.14 Procedural Claim Validator
#
# Objective:
# Validate procedural law claims (deadlines, remand tranches, bail relief fractions, FIR rules)
# against the authoritative BNSS 2023 Procedural Registry and enforce grounded corrections.

import re
from typing import Dict, List, Any, Tuple, Optional

from retrieval.procedural_rules_registry import ProceduralRulesRegistry

class ProceduralClaimValidator:
    def __init__(self):
        self.registry = ProceduralRulesRegistry()

    def validate_and_enforce_procedural_claim(self, query: str, llm_response: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        rule = self.registry.lookup_procedural_rule(query)
        if not rule:
            return True, llm_response, None

        resp_lower = llm_response.lower()
        rule_id = rule["rule_id"]

        # Check Judgment Pronouncement (BNSS 392)
        if rule_id == "BNSS_PROC_392":
            if "30" not in resp_lower or "45" not in resp_lower or "392" not in resp_lower:
                corrected = (
                    f"Under BNSS Section 392, the judgment in every trial in any Criminal Court must be pronounced "
                    f"within 30 days after termination of trial, extendable up to 45 days for recorded reasons."
                )
                return False, corrected, rule

        # Check Police Remand (BNSS 187)
        elif rule_id == "BNSS_PROC_187":
            if "15 days" not in resp_lower or ("40" not in resp_lower and "60" not in resp_lower) or "187" not in resp_lower:
                corrected = (
                    f"Under BNSS Section 187, police custody can be granted for up to 15 days in whole or in parts "
                    f"during the initial 40 or 60 days of the total detention period."
                )
                return False, corrected, rule

        # Check Undertrial Detention (BNSS 479)
        elif rule_id == "BNSS_PROC_479":
            if ("one-third" not in resp_lower and "1/3" not in resp_lower) or "479" not in resp_lower:
                corrected = (
                    f"Under BNSS Section 479, a first-time offender who has never been previously convicted "
                    f"shall be released on bail if they have undergone detention for one-third of the maximum imprisonment period."
                )
                return False, corrected, rule

        # Check Notice of Appearance (BNSS 35(3))
        elif rule_id == "BNSS_PROC_35_3":
            if "35(3)" not in resp_lower and "35" not in resp_lower:
                corrected = (
                    f"Under BNSS Section 35(3), police officers are mandated to issue a notice of appearance "
                    f"to any person suspected of an offence punishable with imprisonment up to 7 years, where arrest is not required."
                )
                return False, corrected, rule

        # Check FIR Registration (BNSS 173)
        elif rule_id == "BNSS_PROC_173":
            if "173" not in resp_lower:
                corrected = (
                    f"Under BNSS Section 173, registration of FIR is mandatory upon receiving information of a cognizable offence, "
                    f"including Zero FIR and electronic FIR (e-FIR)."
                )
                return False, corrected, rule

        return True, llm_response, rule
