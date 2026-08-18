# procedural_rules_registry.py — Nyaya Legal OS Phase 6.18 Fully Hardened Procedural Law & Timeline Registry

from typing import Dict, List, Any, Optional

PROCEDURAL_RULES_REGISTRY = {
    # 1. JUDGMENT PRONOUNCEMENT TIMELINE
    "judgment_pronouncement": {
        "rule_id": "BNSS_PROC_392",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "section": "Section 392",
        "chapter": "Chapter XXIX: The Judgment",
        "topic": "Judgment Pronouncement Timeline",
        "rule_summary": "Under BNSS Section 392, the judgment in every trial in any Criminal Court must be pronounced within 30 days after termination of trial, extendable up to 45 days for recorded reasons.",
        "exact_timeline": "30 days (extendable up to 45 days)",
        "trigger_keywords": ["judgment", "392", "pronouncement of judgment"],
        "source": "Act 46 of 2023, Section 392(1)"
    },

    # 2. POLICE REMAND & DETENTION
    "police_remand": {
        "rule_id": "BNSS_PROC_187",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "section": "Section 187",
        "chapter": "Chapter XII: Information to the Police and Their Powers to Investigate",
        "topic": "Police Custody & Remand Deadlines",
        "rule_summary": "Under BNSS Section 187, police custody can be granted for up to 15 days in whole or in parts during the initial 40 or 60 days of the total detention period.",
        "exact_timeline": "15 days maximum (in parts across initial 40 or 60 days)",
        "trigger_keywords": ["police custody", "remand", "custody period", "187"],
        "source": "Act 46 of 2023, Section 187(2)"
    },

    # 3. UNDERTRIAL DETENTION & BAIL RELIEF
    "undertrial_bail": {
        "rule_id": "BNSS_PROC_479",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "section": "Section 479",
        "chapter": "Chapter XXXV: Provisions as to Bail and Bonds",
        "topic": "Maximum Period for Undertrial Prisoners",
        "rule_summary": "Under BNSS Section 479, a first-time offender who has never been previously convicted shall be released on bail if they have undergone detention for one-third of the maximum imprisonment period.",
        "exact_timeline": "1/3 of max term for first-time offenders; 1/2 of max term for non-first-time offenders",
        "trigger_keywords": ["undertrial", "first-time", "479", "relaxation does bnss section 479"],
        "source": "Act 46 of 2023, Section 479(1)"
    },

    # 4. NOTICE OF APPEARANCE BEFORE ARREST
    "notice_of_appearance": {
        "rule_id": "BNSS_PROC_35_3",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "section": "Section 35(3)",
        "chapter": "Chapter V: Arrest of Persons",
        "topic": "Mandatory Notice of Appearance",
        "rule_summary": "Under BNSS Section 35(3), police officers are mandated to issue a notice of appearance to any person suspected of an offence punishable with imprisonment up to 7 years, where arrest is not required.",
        "exact_timeline": "Mandatory prior to arrest for offences <= 7 years",
        "trigger_keywords": ["notice of appearance", "35(3)", "35"],
        "source": "Act 46 of 2023, Section 35(3)"
    },

    # 5. MANDATORY FIR, e-FIR & ZERO FIR
    "fir_registration": {
        "rule_id": "BNSS_PROC_173",
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "section": "Section 173",
        "chapter": "Chapter XII: Information to the Police and Their Powers to Investigate",
        "topic": "FIR Registration, e-FIR & Zero FIR",
        "rule_summary": "Under BNSS Section 173, registration of FIR is mandatory upon receiving information of a cognizable offence, including Zero FIR and electronic FIR (e-FIR).",
        "exact_timeline": "e-FIR to be signed within 3 days; Preliminary inquiry within 14 days for 3-7 year offences",
        "trigger_keywords": ["zero fir", "e-fir", "fir registration", "173"],
        "source": "Act 46 of 2023, Section 173(1), (3)"
    }
}

import re

class ProceduralRulesRegistry:
    def __init__(self):
        pass

    def lookup_procedural_rule(self, query: str) -> Optional[Dict[str, Any]]:
        q_lower = query.lower()
        for key, entry in PROCEDURAL_RULES_REGISTRY.items():
            for kw in entry["trigger_keywords"]:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                    return entry
        return None
