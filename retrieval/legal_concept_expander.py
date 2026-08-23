"""legal_concept_expander.py — Nyaya Legal OS Legal Concept Extractor & Candidate Expander (Phase 8.2K).

Extracts structured legal concepts and expands them deterministically into provenance-backed candidate sections:
1. Conduct & Offence Elements (Dishonest taking, armed fear, gang robbery, fiduciary breach, online harassment, penetrative assault)
2. Procedural Safeguards (BNSS Notice 35, Search Videography 105, Attachment 107, Remand 187, Bail 479)
3. Evidentiary Proof (BSA Electronic Records 61-63, Custody Discovery 23, Dying Decl 26, Expert 39)
4. Child Protection (POCSO Age 2(1)(d), Penetrative 5/6, Assault 7/8, Harassment 11/12, Reporting 19/21, Procedure 24/33)
"""

import re
from typing import Dict, List, Any, Set, Tuple
from retrieval.near_neighbour_registry import NearNeighbourRegistry
from retrieval.negative_proposition_analyzer import NegativePropositionAnalyzer

class LegalConceptExpander:
    def __init__(self):
        self.near_neighbour_reg = NearNeighbourRegistry()
        self.negation_analyzer = NegativePropositionAnalyzer()

    def extract_concepts_and_expand(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()
        
        # 1. Analyze Negations
        neg_analysis = self.negation_analyzer.analyze_negations(query)
        prohibited_secs = set((p[0].upper(), str(p[1]).upper()) for p in neg_analysis.get("prohibited_sections", []))

        expanded_candidates: List[Dict[str, Any]] = []
        seen_cand_keys: Set[Tuple[str, str]] = set()

        def add_candidate(statute: str, section: str, concept: str, reason: str, conf: float = 0.9):
            st_up = statute.upper()
            sec_clean = str(section).strip().upper()
            key = (st_up, sec_clean)
            if key in prohibited_secs:
                return
            if key not in seen_cand_keys:
                seen_cand_keys.add(key)
                expanded_candidates.append({
                    "statute": st_up,
                    "section": sec_clean,
                    "concept_match": concept,
                    "candidate_reason": reason,
                    "source": "concept_expansion_layer",
                    "confidence": conf
                })

        # ── 2. CONCEPT: THEFT VS SNATCHING VS ROBBERY VS EXTORTION VS DACOITY ─
        if any(w in q_lower for w in ["five or more", "gang of five", "six armed", "seven armed men", "highway robbery by five"]):
            add_candidate("BNS", "310", "dacoity", "Conjoint robbery by five or more armed persons", 0.98)
            add_candidate("BNS", "311", "dacoity_punishment", "Prescribed punishment for dacoity", 0.95)

        elif any(w in q_lower for w in ["gunpoint", "knifepoint", "armed intruder forced", "instant hurt", "armed robbers hold", "robbery"]):
            add_candidate("BNS", "309", "robbery", "Theft or extortion with instant fear of hurt/death", 0.98)
            add_candidate("BNS", "329", "robbery_with_attempt", "Grievous hurt or attempt in robbery", 0.92)

        elif any(w in q_lower for w in ["snatch", "grabbed gold chain", "grabbed purse", "sprinted onto a moving motorcycle", "snatching"]):
            add_candidate("BNS", "304", "snatching", "Sudden grabbing of property from victim body", 0.98)

        elif any(w in q_lower for w in ["threaten to leak", "threatened to publish", "demand letter", "blackmail", "extortion", "threat of arson to extract"]):
            add_candidate("BNS", "308", "extortion", "Coercive extraction of property under fear of injury", 0.98)
            add_candidate("BNS", "351", "criminal_intimidation", "Threat to cause injury or publish defamatory matter", 0.95)

        elif any(w in q_lower for w in ["found lost", "left behind on an empty seat", "found on a train", "pawned diamond necklace"]):
            add_candidate("BNS", "314", "dishonest_misappropriation", "Dishonest conversion of found movable property", 0.98)

        elif any(w in q_lower for w in ["warehouse supervisor sold", "accountant transferred", "fiduciary custody", "entrusted with goods"]):
            add_candidate("BNS", "316", "criminal_breach_of_trust", "Dishonest misappropriation by person entrusted with property", 0.98)

        elif any(w in q_lower for w in ["theft", "stole", "secretly pocketed", "hot-wiring", "takes movable property", "quietly removes"]):
            add_candidate("BNS", "303", "theft", "Dishonest taking of movable property without consent", 0.98)

        # ── 3. CONCEPT: FRAUD, CHEATING & FORGERY ──────────────────────────────
        if any(w in q_lower for w in ["cheating", "fraudulent online", "advance bank transfers", "fake visa", "fake employment", "persuading delivery"]):
            add_candidate("BNS", "318", "cheating", "Fraudulent or dishonest inducement of property delivery", 0.98)
            add_candidate("BNS", "319", "cheating_by_personation", "Cheating by pretending to be someone else", 0.95)

        if any(w in q_lower for w in ["forged", "forgery", "altered title deed", "cloned signature", "fake power of attorney", "fabricated invoices", "altered regulatory notice"]):
            add_candidate("BNS", "336", "forgery", "Making false document with intent to cause damage/fraud", 0.98)
            add_candidate("BNS", "338", "forgery_valuable_security", "Forgery of valuable security or will", 0.95)
            add_candidate("BNS", "340", "using_forged_document", "Using as genuine a forged document", 0.95)

        # ── 4. CONCEPT: HOMICIDE, NEGLIGENCE & PRIVATE DEFENCE ────────────────
        if any(w in q_lower for w in ["private defence", "self-defence", "repelling intruder", "fireplace poker", "strikes back fatally in defence"]):
            add_candidate("BNS", "38", "private_defence_general", "Right of private defence of body and property", 0.98)
            add_candidate("BNS", "41", "private_defence_causing_death", "Right of private defence extending to causing death", 0.98)
            add_candidate("BNS", "44", "private_defence_property_death", "Private defence of property extending to death", 0.95)

        elif any(w in q_lower for w in ["hit-and-run", "rash driving", "intoxicated surgeon", "death by negligence", "pedestrian collision"]):
            add_candidate("BNS", "106", "death_by_negligence", "Causing death by rash or negligent act (including hit-and-run)", 0.98)
            add_candidate("BNS", "281", "rash_driving", "Rash driving on public way endangering life", 0.95)

        elif any(w in q_lower for w in ["murder", "mob lynching", "beat to death", "intentional killing", "culpable homicide"]):
            add_candidate("BNS", "103", "murder", "Punishment for murder (including mob lynching)", 0.98)
            add_candidate("BNS", "105", "culpable_homicide_not_murder", "Culpable homicide not amounting to murder", 0.92)

        # ── 5. CONCEPT: POCSO CHILD PROTECTION ────────────────────────────────
        is_child = any(w in q_lower for w in ["child", "minor", "student", "pocso", "10-year-old", "11-year-old", "12-year-old", "14-year-old", "15-year-old", "17 years", "18 years"])
        if is_child or "pocso" in q_lower:
            if any(w in q_lower for w in ["age definition", "threshold age", "definition of a child", "under 18 years", "2(1)(d)"]):
                add_candidate("POCSO", "2(1)(d)", "pocso_child_age", "Statutory threshold age definition of a child", 0.98)
                add_candidate("POCSO", "2", "pocso_definitions", "General definitions under POCSO", 0.92)

            if any(w in q_lower for w in ["penetrative", "aggravated penetrative", "relative", "domestic household", "sexual act", "arranged transportation"]):
                add_candidate("POCSO", "5", "aggravated_penetrative_assault", "Aggravated penetrative sexual assault elements", 0.98)
                add_candidate("POCSO", "6", "aggravated_penetrative_punishment", "Punishment for aggravated penetrative sexual assault", 0.95)
                add_candidate("POCSO", "3", "penetrative_assault", "Penetrative sexual assault definition", 0.92)
                add_candidate("POCSO", "4", "penetrative_punishment", "Punishment for penetrative sexual assault", 0.92)

            elif any(w in q_lower for w in ["non-penetrative", "touching intimate parts", "sexual touching", "sports coach touching", "sexual assault"]):
                add_candidate("POCSO", "7", "sexual_assault_non_penetrative", "Sexual assault definition (non-penetrative physical contact)", 0.98)
                add_candidate("POCSO", "8", "sexual_assault_punishment", "Punishment for sexual assault", 0.95)
                add_candidate("POCSO", "9", "aggravated_sexual_assault", "Aggravated sexual assault by coach/institution", 0.95)
                add_candidate("POCSO", "10", "aggravated_assault_punishment", "Punishment for aggravated sexual assault", 0.92)

            elif any(w in q_lower for w in ["explicit sexual messages", "sexual harassment", "online communications", "sent explicit", "private photos of minor"]):
                add_candidate("POCSO", "11", "sexual_harassment_child", "Sexual harassment of a child definition", 0.98)
                add_candidate("POCSO", "12", "sexual_harassment_punishment", "Punishment for sexual harassment of a child", 0.95)

            if any(w in q_lower for w in ["report", "reporting", "failure to report", "principal", "headmaster", "in-charge", "mandatory reporting", "concealed"]):
                add_candidate("POCSO", "19", "mandatory_reporting", "Mandatory duty to report offences to police/CWC", 0.98)
                add_candidate("POCSO", "21", "failure_to_report_penalty", "Punishment for failure to report offences", 0.98)

            if any(w in q_lower for w in ["special court", "recording statement", "in-camera", "magistrate statement", "special safeguards", "child friendly"]):
                add_candidate("POCSO", "24", "recording_statement_police", "Procedure for recording statement of child by police", 0.98)
                add_candidate("POCSO", "25", "recording_statement_magistrate", "Recording of child statement under Section 183 BNSS", 0.95)
                add_candidate("POCSO", "33", "special_court_procedure", "Procedure and powers of Special Court", 0.98)
                add_candidate("POCSO", "34", "procedure_age_determination", "Procedure when question arises regarding child age", 0.92)

            if any(w in q_lower for w in ["repeal", "alongside", "continue in force", "overriding", "42a"]):
                add_candidate("POCSO", "42A", "act_not_in_derogation", "POCSO Act not in derogation of other laws", 0.98)
                add_candidate("POCSO", "42", "alternate_punishment", "Offence punishable under POCSO and BNS", 0.95)

        # ── 6. CONCEPT: BNSS PROCEDURAL SAFEGUARDS ────────────────────────────
        if any(w in q_lower for w in ["notice of appearance", "arrest without notice", "under 7 years", "section 35"]):
            add_candidate("BNSS", "35", "notice_of_appearance", "Mandatory notice of appearance prior to arrest", 0.98)

        if any(w in q_lower for w in ["warrantless house search", "videography", "audio-video", "search and seizure", "seizure memo"]):
            add_candidate("BNSS", "105", "search_videography", "Mandatory audio-video electronic recording of search/seizure", 0.98)
            add_candidate("BNSS", "185", "search_by_police_officer", "Search by police officer with recorded grounds", 0.95)

        if any(w in q_lower for w in ["attachment of property", "proceeds of crime", "freeze bank accounts", "attachment powers"]):
            add_candidate("BNSS", "107", "proceeds_attachment", "Attachment and forfeiture of proceeds of crime", 0.98)

        if any(w in q_lower for w in ["police custody", "remand in tranches", "15-day custody", "section 187"]):
            add_candidate("BNSS", "187", "remand_custody", "Police remand in tranches across initial 40/60 days", 0.98)

        if any(w in q_lower for w in ["undertrial bail", "one-third sentence", "detention without trial", "statutory bail"]):
            add_candidate("BNSS", "479", "undertrial_statutory_bail", "Statutory bail for first-time and long-term undertrials", 0.98)

        if any(w in q_lower for w in ["zero fir", "inter-state journey", "transit jurisdiction", "fir registration"]):
            add_candidate("BNSS", "173", "information_in_cognizable_cases", "Registration of FIR / Zero FIR", 0.98)
            add_candidate("BNSS", "197", "jurisdiction_during_journey", "Jurisdiction for offences committed on journey/transit", 0.95)

        # ── 7. CONCEPT: BSA EVIDENCE ADMISSIBILITY & PROOF ────────────────────
        if any(w in q_lower for w in ["electronic record", "whatsapp", "cctv footage", "hash value", "certificate under section 63", "digital proof", "server logs"]):
            add_candidate("BSA", "61", "electronic_evidence_admissibility", "Admissibility of electronic records", 0.98)
            add_candidate("BSA", "62", "electronic_evidence_conditions", "Conditions for admissibility of electronic records", 0.95)
            add_candidate("BSA", "63", "electronic_record_certificate", "Certificate requirements for electronic records", 0.98)

        if any(w in q_lower for w in ["discovery statement", "disclosure statement", "recovered from a ditch", "hidden weapon in well", "custody confession leading to recovery"]):
            add_candidate("BSA", "23", "custody_discovery", "Admissibility of information leading to discovery of fact in custody", 0.98)

        if any(w in q_lower for w in ["dying declaration", "statement as to cause of death", "burn victim in hospital"]):
            add_candidate("BSA", "26", "dying_declaration", "Admissibility of statements by deceased regarding cause of death", 0.98)

        if any(w in q_lower for w in ["expert opinion", "ballistics", "handwriting expert", "medical board", "forensic inspection"]):
            add_candidate("BSA", "39", "expert_opinion", "Admissibility of opinions of experts in science/art", 0.98)

        if any(w in q_lower for w in ["dowry death presumption", "cruelty for dowry shortly before death"]):
            add_candidate("BSA", "118", "dowry_death_presumption", "Statutory presumption as to dowry death", 0.98)

        return {
            "query": query,
            "negation_analysis": neg_analysis,
            "expanded_candidates": expanded_candidates,
            "statute_to_expanded_sections": self._group_by_statute(expanded_candidates)
        }

    def _group_by_statute(self, candidates: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        res: Dict[str, List[str]] = {}
        for c in candidates:
            st = c["statute"]
            sec = c["section"]
            if st not in res:
                res[st] = []
            if sec not in res[st]:
                res[st].append(sec)
        return res
