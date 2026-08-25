"""legal_issue_classifier.py — Nyaya Legal OS Intermediate Legal Issue Classifier (Phase 8.2I).

Extracts explicit intermediate structured legal issue representations from factual narratives:
1. Primary Substantive Issues (Offence elements, near-neighbour discrimination)
2. Procedural & Investigative Issues (Arrest notice, search videography, attachment, remand, bail)
3. Evidentiary Issues (Electronic records & certs, confessions & discovery, expert testimony, presumptions)
4. Special Child Protection Issues (POCSO granular discrimination: penetrative, assault, harassment, reporting, procedure)
5. Negative Distractor Identification (Provisions sharing vocabulary but legally inapplicable)
"""

import re
from typing import Dict, List, Any, Set, Tuple

class LegalIssueClassifier:
    def __init__(self):
        pass

    def classify_issues(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()
        
        primary_issues = []
        secondary_issues = []
        negative_distractors = set()
        active_statutes = set()
        targeted_sections: Dict[str, List[str]] = {}

        def add_issue(domain: str, concept: str, statute: str, sections: List[str], is_primary: bool = True, fact_triggers: List[str] = None):
            active_statutes.add(statute)
            if statute not in targeted_sections:
                targeted_sections[statute] = []
            for s in sections:
                if s not in targeted_sections[statute]:
                    targeted_sections[statute].append(s)
            
            entry = {
                "domain": domain,
                "concept": concept,
                "statute": statute,
                "target_sections": sections,
                "fact_triggers": fact_triggers or []
            }
            if is_primary:
                primary_issues.append(entry)
            else:
                secondary_issues.append(entry)

        # ── 1. POCSO SPECIAL STATUTE DISCRIMINATION ──────────────────────────────────
        is_child = any(w in q_lower for w in [
            "child", "minor", "student", "pocso", "10-year-old", "11-year-old", "12-year-old",
            "14-year-old", "15-year-old", "16-year-old", "17-year-old", "children home", "juvenile", "below 18", "under 18"
        ])

        if is_child:
            active_statutes.add("POCSO")
            # A. Age definition
            if any(w in q_lower for w in ["age definition", "definition of a child", "who is a child", "under 18 years", "2(1)(d)"]):
                add_issue("child_protection", "pocso_child_definition", "POCSO", ["2(1)(d)", "2"], is_primary=True, fact_triggers=["age_definition"])

            # B. Penetrative / Aggravated Penetrative Sexual Assault
            if any(w in q_lower for w in [
                "penetrative", "aggravated penetrative", "rape", "domestic residence", "relative", 
                "administrator sexually exploiting", "sexual act", "arranged transportation", "aggravated offence",
                "partly online and partly offline"
            ]):
                add_issue("child_protection", "pocso_penetrative_sexual_assault", "POCSO", ["5", "6", "3", "4"], is_primary=True, fact_triggers=["penetrative_act", "aggravated_custody"])
                if not any(w in q_lower for w in ["online", "messages", "harassment"]):
                    negative_distractors.update([("POCSO", "11"), ("POCSO", "12")])

            # C. Non-Penetrative Sexual Assault / Touching
            if any(w in q_lower for w in [
                "non-penetrative", "sexual touching", "sexual assault", "touching of a 12-year-old", "physical sexual contact",
                "coercing the child during an in-person meeting", "coercing the child", "in-person meeting"
            ]):
                add_issue("child_protection", "pocso_sexual_assault", "POCSO", ["7", "8", "9", "10"], is_primary=True, fact_triggers=["sexual_touching"])
                if not any(w in q_lower for w in ["penetrative", "rape"]):
                    negative_distractors.update([("POCSO", "3"), ("POCSO", "4"), ("POCSO", "5"), ("POCSO", "6")])

            # D. Sexual Harassment / Online Messages
            if any(w in q_lower for w in [
                "explicit sexual messages", "sexual harassment", "online communications", "sent explicit", 
                "private photos of minor", "messages to a 14-year-old", "messages to a student", "account registered to the accused",
                "online and partly offline", "sexually explicit messages", "explicit messages on instagram",
                "never touched", "no physical contact", "without touching", "non-contact sexual harassment"
            ]):
                add_issue("child_protection", "pocso_sexual_harassment", "POCSO", ["11", "12"], is_primary=True, fact_triggers=["explicit_messages_harassment"])

            # E. Mandatory Reporting Obligations & Institutional Failure
            if any(w in q_lower for w in [
                "report", "reporting", "failure to report", "headmaster", "in-charge", "mandatory reporting", 
                "filed away the complaint", "without reporting", "failed to report the incident", "failed to report"
            ]):
                add_issue("child_protection", "pocso_mandatory_reporting", "POCSO", ["19", "21"], is_primary=False, fact_triggers=["reporting_duty_breach"])

            # F. Special Court Procedures & Child Statement Recording
            if any(w in q_lower for w in [
                "special court", "recording the statement", "in-camera", "powers and duties of the special court", 
                "procedure before special court", "section 24", "section 33", "statement to a magistrate",
                "special safeguards", "in-camera procedure", "medical examination report"
            ]):
                add_issue("child_protection", "pocso_procedure", "POCSO", ["24", "25", "33", "34", "35", "37"], is_primary=False, fact_triggers=["special_court_safeguards"])

            # G. Statutory Overriding Effect (Section 42A)
            if any(w in q_lower for w in ["repeal the pocso", "pocso continue in force", "overriding effect", "alongside", "punishable under both", "42a"]):
                add_issue("child_protection", "pocso_overriding", "POCSO", ["42", "42A"], is_primary=False, fact_triggers=["statutory_non_derogation"])

        # ── 2. BNS SUBSTANTIVE OFFENCE DISCRIMINATION ───────────────────────────────
        # A. Theft vs Snatching vs Extortion vs Robbery vs Dacoity vs Misappropriation vs Breach of Trust
        if any(w in q_lower for w in ["five or more", "gang of five", "group of five", "highway robbery by five", "stopped a delivery van"]):
            add_issue("substantive_offence", "dacoity", "BNS", ["310", "311"], is_primary=True, fact_triggers=["gang_five_armed"])
            negative_distractors.update([("BNS", "303"), ("BNS", "304"), ("BNS", "308")])

        elif any(w in q_lower for w in ["knife-point", "gun-point", "brandished weapons", "armed intruder forced entry and demanded", "robbery"]):
            add_issue("substantive_offence", "robbery", "BNS", ["309", "329"], is_primary=True, fact_triggers=["armed_fear_instant_hurt"])
            negative_distractors.update([("BNS", "303"), ("BNS", "304")])

        elif any(w in q_lower for w in ["snatch", "grabbed gold chain", "grabbed chain", "snatching", "sprinted onto a moving"]):
            add_issue("substantive_offence", "snatching", "BNS", ["304"], is_primary=True, fact_triggers=["sudden_grabbing_body"])
            negative_distractors.update([("BNS", "303"), ("BNS", "308")])

        elif any(w in q_lower for w in [
            "threaten to leak", "threatened to publish", "threatening to publish", "threatens to publish",
            "publish edited intimate images", "publish intimate images", "anonymous demand letter",
            "extortion", "extort", "leak private photos", "threat of arson to extract"
        ]):
            add_issue("substantive_offence", "extortion", "BNS", ["308", "351"], is_primary=True, fact_triggers=["coercive_demand_fear"])
            negative_distractors.update([("BNS", "303")])

        elif any(w in q_lower for w in ["found a lost", "finding lost", "found on a train", "left behind on an empty seat", "discovered movable and kept", "pawned diamond necklace"]):
            add_issue("substantive_offence", "dishonest_misappropriation", "BNS", ["314"], is_primary=True, fact_triggers=["found_lost_property_conversion"])
            negative_distractors.update([("BNS", "303"), ("BNS", "316")])

        elif any(w in q_lower for w in ["warehouse supervisor sold", "accountant transferred", "employee downloaded credit card", "entrusted with custody", "misappropriated entrusted goods", "cashier taking cash"]):
            add_issue("substantive_offence", "criminal_breach_of_trust", "BNS", ["316"], is_primary=True, fact_triggers=["entrustment_dominion_breach"])
            if any(w in q_lower for w in ["cash register", "theft"]):
                add_issue("substantive_offence", "theft", "BNS", ["303"], is_primary=True, fact_triggers=["dishonest_taking"])

        elif any(w in q_lower for w in ["theft", "stole", "secretly pocketed", "hot-wiring a motorcycle", "unauthorized removal of property", "takes movable property"]):
            add_issue("substantive_offence", "theft", "BNS", ["303"], is_primary=True, fact_triggers=["dishonest_movable_taking"])

        # B. Cheating & Forgery
        if any(w in q_lower for w in ["cheating", "fraudulent online", "advance bank transfers", "booking deposits and transferred offshore", "fake visa", "issued five cheques knowing account was closed", "deceived investor", "persuades an investor", "transfer funds"]):
            add_issue("substantive_offence", "cheating", "BNS", ["318", "319"], is_primary=True, fact_triggers=["fraudulent_inducement"])

        if any(w in q_lower for w in ["forged", "forgery", "altered registration", "altered odometer", "cloned signature", "presented a forged cheque", "altered regulatory notice", "fabricated duplicate invoices", "counterfeit expiry labels", "revenue documents fraudulent sale", "altered letterhead", "altered figures"]):
            add_issue("substantive_offence", "forgery", "BNS", ["336", "338", "340"], is_primary=True, fact_triggers=["false_document_creation"])

        # C. Homicide vs Negligence vs Private Defence
        if any(w in q_lower for w in ["private defence", "self-defence", "midnight intruder crowbar struck", "apprehension of death", "repelling attack in house"]):
            add_issue("substantive_offence", "private_defence", "BNS", ["38", "40", "41", "44"], is_primary=True, fact_triggers=["justified_repel_imminent_danger"])
            negative_distractors.update([("BNS", "103"), ("BNS", "106")])

        elif any(w in q_lower for w in ["hit-and-run", "rash driving", "intoxicated surgeon", "substandard concrete flyover", "hoarding collapse", "death by negligence", "pedestrian collision"]):
            add_issue("substantive_offence", "death_by_negligence", "BNS", ["106", "281", "288"], is_primary=True, fact_triggers=["rash_negligent_causing_death"])
            negative_distractors.update([("BNS", "103")])

        elif any(w in q_lower for w in ["murder", "mob lynching", "beat to death", "seven armed men", "culpable homicide", "intentional killing"]):
            add_issue("substantive_offence", "murder_and_homicide", "BNS", ["103", "105", "190"], is_primary=True, fact_triggers=["intentional_group_killing"])

        # D. Public Health, Poison & Adulteration
        if any(w in q_lower for w in ["toxic acidic waste", "discharged untreated waste", "mixed toxic industrial dye", "adulteration of food", "expired antibiotic syrups", "poison"]):
            add_issue("substantive_offence", "public_health_poison", "BNS", ["272", "274", "276", "277"], is_primary=True, fact_triggers=["toxic_substance_endangerment"])

        # E. Stalking, Voyeurism & Arson
        if any(w in q_lower for w in ["stalking", "spyware to record calls", "repeatedly following"]):
            add_issue("substantive_offence", "stalking", "BNS", ["78"], is_primary=True, fact_triggers=["electronic_physical_monitoring"])

        if any(w in q_lower for w in ["voyeurism", "hidden optical sensor", "changing room cubicles", "technician copying private videos"]):
            add_issue("substantive_offence", "voyeurism", "BNS", ["77"], is_primary=True, fact_triggers=["capturing_intimate_images"])

        if any(w in q_lower for w in ["arson", "set fire to commercial textile", "mischief by fire"]):
            add_issue("substantive_offence", "arson_mischief", "BNS", ["326", "324"], is_primary=True, fact_triggers=["intentional_fire_destruction"])

        if any(w in q_lower for w in ["severed drinking water", "utilities cut", "locked in basement", "wrongful confinement"]):
            add_issue("substantive_offence", "restraint_mischief", "BNS", ["126", "127", "324"], is_primary=True, fact_triggers=["utility_severance_confinement"])

        if any(w in q_lower for w in ["counterfeit currency", "printing replica 500-rupee", "offset press"]):
            add_issue("substantive_offence", "counterfeiting", "BNS", ["231", "232", "234"], is_primary=True, fact_triggers=["currency_counterfeiting"])

        if any(w in q_lower for w in ["defamation", "pamphlets alleging organ trafficking", "injurious character imputations"]):
            add_issue("substantive_offence", "defamation", "BNS", ["356"], is_primary=True, fact_triggers=["public_reputational_harm"])

        # ── 3. BNSS PROCEDURAL ISSUE DISCRIMINATION ─────────────────────────────────
        if any(w in q_lower for w in ["arrest without notice", "section 35 notice", "notice of appearance", "safeguard against arrest", "bnss section 35"]):
            add_issue("criminal_procedure", "arrest_safeguards", "BNSS", ["35", "35(1)"], is_primary=False, fact_triggers=["pre_arrest_notice_mandate"])

        if any(w in q_lower for w in ["warrantless house search", "search and seizure", "videography", "audio-video", "seizure memo", "bnss section 105", "without recorded reasons"]):
            add_issue("criminal_procedure", "search_and_seizure", "BNSS", ["105", "185"], is_primary=False, fact_triggers=["videography_search_safeguard"])

        if any(w in q_lower for w in ["attachment of property", "proceeds of crime", "freeze bank accounts", "bnss section 107", "attachment powers"]):
            add_issue("criminal_procedure", "proceeds_attachment", "BNSS", ["107", "107(1)"], is_primary=False, fact_triggers=["proceeds_of_crime_attachment"])

        if any(w in q_lower for w in ["police custody", "remand in tranches", "15-day police custody", "bnss section 187", "transit remand"]):
            add_issue("criminal_procedure", "police_remand", "BNSS", ["187", "187(1)", "187(2)", "187(3)"], is_primary=False, fact_triggers=["remand_custody_powers"])

        if any(w in q_lower for w in ["undertrial bail", "one-third sentence", "detention without trial", "bnss section 479", "bnss section 480", "bail in non-bailable"]):
            add_issue("criminal_procedure", "undertrial_bail", "BNSS", ["479", "480"], is_primary=False, fact_triggers=["statutory_bail_safeguards"])

        if any(w in q_lower for w in [
            "zero fir", "inter-state journey", "jurisdiction during transit", "bnss section 173",
            "bnss section 197", "electronic fir", "e-fir", "online fir", "fir electronically",
            "register the fir electronically"
        ]) or ("fir" in q_lower and "electronically" in q_lower):
            add_issue("criminal_procedure", "fir_and_jurisdiction", "BNSS", ["173", "197"], is_primary=False, fact_triggers=["transit_jurisdiction_fir"])

        # ── 4. BSA EVIDENCE ISSUE DISCRIMINATION ───────────────────────────────────
        if any(w in q_lower for w in [
            "electronic record", "whatsapp", "chat logs", "cctv footage", "hash value", "certificate under section 63", 
            "digital proof", "phone backup", "restored from backup", "electronic extraction report", "what evidence is required to prove",
            "bsa section 63", "section 65b equivalent", "server logs", "digital copy"
        ]) or "screenshots" in q_lower:
            add_issue("law_of_evidence", "electronic_evidence", "BSA", ["61", "62", "63", "63(1)", "63(4)"], is_primary=False, fact_triggers=["electronic_admissibility_cert"])

        if any(w in q_lower for w in ["discovery statement", "disclosure statement", "weapon recovered from a ditch", "bsa section 23"]):
            add_issue("law_of_evidence", "disclosure_recovery", "BSA", ["23", "23(1)"], is_primary=False, fact_triggers=["fact_discovered_information"])

        if any(w in q_lower for w in ["dying declaration", "declaration before death", "bsa section 26"]):
            add_issue("law_of_evidence", "dying_declaration", "BSA", ["26"], is_primary=False, fact_triggers=["statement_cause_of_death"])

        if any(w in q_lower for w in ["expert opinion", "handwriting expert", "ballistics report", "medical expert", "mechanical inspection", "bsa section 39"]):
            add_issue("law_of_evidence", "expert_opinion", "BSA", ["39"], is_primary=False, fact_triggers=["specialized_expert_testimony"])

        if any(w in q_lower for w in ["dowry death presumption", "bsa section 118"]):
            add_issue("law_of_evidence", "dowry_presumption", "BSA", ["118"], is_primary=False, fact_triggers=["statutory_presumption_dowry"])

        # ── 5. TRANSITION & SAVINGS (BNS 358 / BNSS 531 / BSA 170) ─────────────────
        if any(w in q_lower for w in ["transition", "repeal", "savings", "pre-2024", "before 1 july 2024", "crpc 531", "bnss 531", "bns 358", "bsa 170"]):
            add_issue("transition_law", "statutory_repeal_savings", "BNS", ["358"], is_primary=False, fact_triggers=["repeal_bns"])
            add_issue("transition_law", "procedural_savings", "BNSS", ["531"], is_primary=False, fact_triggers=["procedural_pending_trial"])
            add_issue("transition_law", "evidence_savings", "BSA", ["170"], is_primary=False, fact_triggers=["evidence_repeal"])

        return {
            "query": query,
            "primary_issues": primary_issues,
            "secondary_issues": secondary_issues,
            "active_statutes": list(active_statutes),
            "targeted_sections": targeted_sections,
            "negative_distractors": list(negative_distractors),
            "is_multi_statute": len(active_statutes) > 1
        }
