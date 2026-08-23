"""negative_proposition_analyzer.py — Nyaya Legal OS Negative Proposition & Negation Analyzer (Phase 8.2K).

Analyzes queries for explicit factual negations, questioned propositions, and prohibited sections:
1. Distinguishes ASSERTED FACT vs NEGATED FACT (e.g. "without consent" vs "without penetration").
2. Identifies QUESTIONED PROPOSITIONS (e.g. "Does simple theft apply when gunpoint force is used?").
3. Detects PROHIBITED CANDIDATE SECTIONS where essential statutory ingredients are explicitly negated.
"""

import re
from typing import Dict, List, Any, Set, Tuple

class NegativePropositionAnalyzer:
    def __init__(self):
        pass

    def analyze_negations(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()
        
        negated_elements = set()
        prohibited_sections = set()
        asserted_elements = set()
        questioned_propositions = []

        # ── 1. POCSO NEGATION PATTERNS ─────────────────────────────────────────
        # "without penetrative conduct" / "non-penetrative" -> Negates POCSO 3/4/5/6
        if any(p in q_lower for p in ["without penetrative", "non-penetrative", "no penetration", "without penetration"]):
            negated_elements.add("penetrative_act")
            prohibited_sections.update([("POCSO", "3"), ("POCSO", "4"), ("POCSO", "5"), ("POCSO", "6")])
            asserted_elements.add("non_penetrative_touching")

        # "online only" / "no physical contact" / "no in-person meeting" -> Negates POCSO 3/4/5/6/7/8
        if any(p in q_lower for p in ["no physical contact", "no in-person contact", "online only", "messages only", "without physical touching"]):
            negated_elements.add("physical_sexual_contact")
            prohibited_sections.update([("POCSO", "3"), ("POCSO", "4"), ("POCSO", "5"), ("POCSO", "6"), ("POCSO", "7"), ("POCSO", "8")])
            asserted_elements.add("explicit_sexual_messages")

        # ── 2. PROPERTY OFFENCE NEGATION PATTERNS ──────────────────────────────
        # "armed force present" / "gunpoint" / "held at knifepoint" -> Negates Simple Theft 303
        if any(p in q_lower for p in ["at gunpoint", "at knifepoint", "armed force", "fear of instant hurt", "brandished weapons"]):
            asserted_elements.add("armed_fear_instant_hurt")
            prohibited_sections.add(("BNS", "303"))

        # "gang of five or more" / "highway robbery by 6" -> Negates simple robbery 309, asserts dacoity 310
        if any(p in q_lower for p in ["five or more", "six armed", "seven armed", "gang of five", "group of six"]):
            asserted_elements.add("gang_of_five_or_more")
            prohibited_sections.add(("BNS", "309"))

        # "found on empty seat" / "not taken from possession" -> Negates Theft 303, CBT 316
        if any(p in q_lower for p in ["left behind on", "found lost", "discovered on empty seat", "not taken from possession"]):
            asserted_elements.add("found_lost_property")
            prohibited_sections.update([("BNS", "303"), ("BNS", "316")])

        # ── 3. HOMICIDE VS NEGLIGENCE NEGATION PATTERNS ────────────────────────
        # "accidental collision" / "no intention to kill" / "rash driving" -> Negates Murder 103
        if any(p in q_lower for p in ["no intent to kill", "without intent to kill", "rash and negligent", "hit-and-run", "accidental collision"]):
            negated_elements.add("intention_to_cause_death")
            asserted_elements.add("rash_or_negligent_act")
            prohibited_sections.add(("BNS", "103"))

        # ── 4. QUESTIONED PROPOSITIONS (Negative Question Detection) ───────────
        # e.g., "Does BNS 303 apply when force is used?"
        if any(p in q_lower for p in ["does simple theft apply", "does theft apply when", "does murder apply to rash", "does bns automatically repeal pocso", "does sexual harassment apply to penetrative"]):
            questioned_propositions.append("negative_element_test")

        return {
            "negated_elements": list(negated_elements),
            "asserted_elements": list(asserted_elements),
            "prohibited_sections": list(prohibited_sections),
            "questioned_propositions": questioned_propositions,
            "has_negations": len(negated_elements) > 0 or len(prohibited_sections) > 0
        }
