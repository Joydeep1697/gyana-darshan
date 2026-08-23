"""query_analyzer.py — Nyaya Legal OS Multi-Issue Query Decomposition & Concept Expansion (Phase 8.2H).

Decomposes complex legal queries and factual narratives into typed parallel branches:
1. Substantive Penal Issues (BNS 2023)
2. Procedural & Jurisdictional Issues (BNSS 2023)
3. Evidence & Electronic Records Issues (BSA 2023)
4. Special Statutes & Transition Law (POCSO 2012 / BNS 358 / BNSS 531)
"""

import re
from typing import Dict, List, Any, Set
from retrieval.legal_ontology import LegalOntologyExpander

class LegalQueryAnalyzer:
    def __init__(self):
        self.ontology_expander = LegalOntologyExpander()

    def analyze_query(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()
        
        # 1. Extract from Comprehensive Legal Ontology
        ontology_res = self.ontology_expander.extract_concepts_and_sections(query)
        matched_concepts = ontology_res["matched_concepts"]
        candidate_statutes = set(ontology_res["active_statutes"])
        candidate_sections_by_statute = ontology_res["candidate_sections_by_statute"]
        all_candidate_sections = set(ontology_res["all_candidate_sections"])
        enriched_tokens = set(ontology_res["enriched_tokens"])

        # 2. Decompose Issue Branches:
        
        # Branch A: Substantive Penal Liability (BNS)
        if any(w in q_lower for w in [
            "bns", "bharatiya nyaya", "ipc", "indian penal code", "murder", "theft", "extortion", "robbery", 
            "dacoity", "misappropriation", "breach of trust", "cheating", "forgery", "penal liability", 
            "substantive penal", "substantive offence", "criminal liability", "offence", "assault", "hurt",
            "private defence", "self-defence", "negligence", "rash driving", "hit-and-run", "defamation",
            "intimidation", "counterfeit", "poison", "adulteration", "voyeurism", "stalking", "arson"
        ]):
            candidate_statutes.add("BNS")

        # Branch B: Criminal Procedure & Investigation (BNSS)
        if any(w in q_lower for w in [
            "bnss", "bharatiya nagarik", "crpc", "criminal procedure", "remand", "custody", "police custody", 
            "bail", "arrest", "notice", "fir", "attachment of property", "attachment", "search and seizure", 
            "search", "seizure", "warrantless", "procedural", "transit remand", "undertrial", "zero fir"
        ]):
            candidate_statutes.add("BNSS")
            if "BNSS" not in candidate_sections_by_statute:
                candidate_sections_by_statute["BNSS"] = []
            if any(w in q_lower for w in ["arrest", "notice", "safeguard", "35"]):
                candidate_sections_by_statute["BNSS"].extend(["35", "35(1)"])
                all_candidate_sections.update(["35", "35(1)"])
            if any(w in q_lower for w in ["search", "seizure", "videography", "audio-video", "warrantless", "device", "phone", "105"]):
                candidate_sections_by_statute["BNSS"].extend(["105", "185"])
                all_candidate_sections.update(["105", "185"])
            if any(w in q_lower for w in ["attachment", "proceeds", "crime", "property", "assets", "freeze", "107"]):
                candidate_sections_by_statute["BNSS"].extend(["107", "107(1)"])
                all_candidate_sections.update(["107", "107(1)"])
            if any(w in q_lower for w in ["remand", "custody", "police custody", "15-day", "tranches", "187"]):
                candidate_sections_by_statute["BNSS"].extend(["187", "187(1)", "187(2)", "187(3)"])
                all_candidate_sections.update(["187", "187(1)", "187(2)", "187(3)"])
            if any(w in q_lower for w in ["undertrial", "bail", "one-third", "half", "479", "480"]):
                candidate_sections_by_statute["BNSS"].extend(["479", "480"])
                all_candidate_sections.update(["479", "480"])

        # Branch C: Law of Evidence & Admissibility (BSA)
        if any(w in q_lower for w in [
            "bsa", "bharatiya sakshya", "iea", "evidence act", "electronic record", "electronic evidence",
            "certificate", "hash", "screenshot", "screenshots", "cctv", "backup", "restored", "admissibility", 
            "what evidence is required", "evidence is required", "how is it proved", "evidence to prove", 
            "admissibility of evidence", "digital proof", "digital extraction", "whatsapp", "chat", "logs",
            "discovery", "disclosure statement", "weapon recovered", "dying declaration", "expert", "forensic",
            "ballistics", "handwriting", "dowry presumption"
        ]):
            candidate_statutes.add("BSA")
            if "BSA" not in candidate_sections_by_statute:
                candidate_sections_by_statute["BSA"] = []
            if any(w in q_lower for w in ["electronic", "record", "certificate", "hash", "screenshot", "cctv", "backup", "whatsapp", "chat", "digital", "admissibility", "61", "62", "63"]):
                candidate_sections_by_statute["BSA"].extend(["61", "62", "63", "63(1)", "63(4)"])
                all_candidate_sections.update(["61", "62", "63", "63(1)", "63(4)"])
            if any(w in q_lower for w in ["discovery", "disclosure", "weapon", "recovery", "ditch", "23"]):
                candidate_sections_by_statute["BSA"].extend(["23", "23(1)"])
                all_candidate_sections.update(["23", "23(1)"])
            if any(w in q_lower for w in ["dying declaration", "declaration", "26"]):
                candidate_sections_by_statute["BSA"].extend(["26"])
                all_candidate_sections.update(["26"])
            if any(w in q_lower for w in ["expert", "forensic", "handwriting", "ballistics", "mechanical", "doctor", "39"]):
                candidate_sections_by_statute["BSA"].extend(["39"])
                all_candidate_sections.update(["39"])
            if any(w in q_lower for w in ["dowry", "presumption", "118"]):
                candidate_sections_by_statute["BSA"].extend(["118"])
                all_candidate_sections.update(["118"])

        # Branch D: Special Child Protection (POCSO)
        if any(w in q_lower for w in [
            "pocso", "child", "minor", "protection of children", "10-year-old", "11-year-old", "12-year-old", 
            "14-year-old", "15-year-old", "16-year-old", "17-year-old", "student", "children home", "juvenile"
        ]):
            candidate_statutes.add("POCSO")
            if "POCSO" not in candidate_sections_by_statute:
                candidate_sections_by_statute["POCSO"] = []
            if any(w in q_lower for w in ["penetrative", "aggravated penetrative", "rape", "domestic", "administrator", "relative"]):
                candidate_sections_by_statute["POCSO"].extend(["3", "4", "5", "6"])
                all_candidate_sections.update(["3", "4", "5", "6"])
            if any(w in q_lower for w in ["touching", "non-penetrative", "sexual assault"]):
                candidate_sections_by_statute["POCSO"].extend(["7", "8", "9", "10"])
                all_candidate_sections.update(["7", "8", "9", "10"])
            if any(w in q_lower for w in ["messages", "harassment", "explicit", "online"]):
                candidate_sections_by_statute["POCSO"].extend(["11", "12"])
                all_candidate_sections.update(["11", "12"])
            if any(w in q_lower for w in ["report", "reporting", "failure to report", "headmaster", "mandatory"]):
                candidate_sections_by_statute["POCSO"].extend(["19", "21"])
                all_candidate_sections.update(["19", "21"])
            if any(w in q_lower for w in ["special court", "recording", "statement", "procedure", "in-camera"]):
                candidate_sections_by_statute["POCSO"].extend(["24", "25", "33", "34", "35", "37"])
                all_candidate_sections.update(["24", "25", "33", "34", "35", "37"])
            if any(w in q_lower for w in ["repeal", "override", "derogation", "both", "alongside", "42", "42a"]):
                candidate_sections_by_statute["POCSO"].extend(["42", "42A"])
                all_candidate_sections.update(["42", "42A"])
            if any(w in q_lower for w in ["age", "definition", "below 18", "under 18"]):
                candidate_sections_by_statute["POCSO"].extend(["2(1)(d)", "2"])
                all_candidate_sections.update(["2(1)(d)", "2"])

        # 3. Check Transition & Savings Queries
        is_transition = False
        if any(term in q_lower for term in ["transition", "repeal", "savings", "retrospective", "pre-2024", "before 1 july 2024", "crpc 531", "bnss 531", "bns 358", "bsa 170", "pending trial", "prior to july"]):
            is_transition = True
            candidate_statutes.add("BNS")
            candidate_statutes.add("BNSS")
            candidate_statutes.add("BSA")
            if "BNS" not in candidate_sections_by_statute: candidate_sections_by_statute["BNS"] = []
            if "BNSS" not in candidate_sections_by_statute: candidate_sections_by_statute["BNSS"] = []
            candidate_sections_by_statute["BNS"].append("358")
            candidate_sections_by_statute["BNSS"].append("531")
            all_candidate_sections.add("358")
            all_candidate_sections.add("531")

        # 4. Extract Explicit Section References (e.g. 'Section 303', 'Sec 187', 'u/s 42A')
        explicit_secs = re.findall(r'(?:section|sec\.?|§|u/s|under\s+section)\s+(\d+[A-Za-z]*(?:\(\w+\))?)', query, re.IGNORECASE)
        for s in explicit_secs:
            clean_s = s.strip()
            all_candidate_sections.add(clean_s)
            for st in candidate_statutes:
                if st not in candidate_sections_by_statute: candidate_sections_by_statute[st] = []
                candidate_sections_by_statute[st].append(clean_s)

        # 5. Multi-Statute Decision
        is_multi_statute = len(candidate_statutes) > 1 or is_transition

        return {
            "query": query,
            "matched_concepts": matched_concepts,
            "candidate_statutes": list(candidate_statutes),
            "candidate_sections": list(all_candidate_sections),
            "statute_to_candidate_sections": candidate_sections_by_statute,
            "is_multi_statute": is_multi_statute,
            "is_transition": is_transition,
            "enriched_tokens": list(enriched_tokens)
        }
