# query_analyzer.py — Nyaya Legal OS Multi-Issue Query Decomposition & Concept Expansion (Phase 8.2C Hardened)

import re
from typing import Dict, List, Any, Set

CONCEPT_MAPPINGS = [
    # --- SUBSTANTIVE OFFENCES (BNS / IPC) ---
    {
        "concept": "theft",
        "statute": "BNS",
        "target_sections": ["303", "303(1)", "303(2)"],
        "triggers": [
            "theft", "steal", "stealing", "stole", "secretly takes movable property",
            "dishonestly takes", "without consent takes movable", "takes another person's movable property without consent"
        ]
    },
    {
        "concept": "extortion",
        "statute": "BNS",
        "target_sections": ["308", "308(1)", "308(2)"],
        "triggers": [
            "extortion", "threatens another with injury to obtain", "threatens with injury to deliver property",
            "threatens to obtain money or property", "puts in fear of injury to deliver",
            "threatens a victim to obtain", "threatens to obtain delivery of money", "obtain delivery of money"
        ]
    },
    {
        "concept": "robbery",
        "statute": "BNS",
        "target_sections": ["309", "309(1)", "309(2)"],
        "triggers": [
            "robbery", "fear of immediate harm", "fear of instant death", "fear of instant hurt",
            "puts that person in fear of immediate harm", "takes property by putting"
        ]
    },
    {
        "concept": "dacoity",
        "statute": "BNS",
        "target_sections": ["310", "310(1)", "310(2)"],
        "triggers": [
            "dacoity", "jointly commit robbery", "planned group operation robbery",
            "five or more persons jointly commit robbery"
        ]
    },
    {
        "concept": "mischief",
        "statute": "BNS",
        "target_sections": ["324", "324(1)", "324(2)"],
        "triggers": [
            "mischief", "deliberately damages another's property", "causing loss without taking",
            "destroys property causing wrongful loss"
        ]
    },
    {
        "concept": "dishonest_misappropriation",
        "statute": "BNS",
        "target_sections": ["314", "314(1)"],
        "triggers": [
            "dishonest misappropriation", "dishonestly converts movable property",
            "converts to own use movable property"
        ]
    },
    {
        "concept": "cheating",
        "statute": "BNS",
        "target_sections": ["318", "318(1)", "318(4)"],
        "triggers": [
            "cheating", "dishonestly inducing delivery of property", "deceiving any person fraudulently"
        ]
    },
    {
        "concept": "forgery",
        "statute": "BNS",
        "target_sections": ["335", "336", "340"],
        "triggers": [
            "forgery", "forges a document", "making a false document", "false electronic record",
            "uses a forged document", "forged electronic record"
        ]
    },
    {
        "concept": "criminal_intimidation",
        "statute": "BNS",
        "target_sections": ["351", "351(1)", "351(2)"],
        "triggers": [
            "criminal intimidation", "threatens another with injury to person reputation",
            "threatens another with injury to person, reputation, or property to cause alarm",
            "threatens to cause alarm"
        ]
    },
    {
        "concept": "defamation",
        "statute": "BNS",
        "target_sections": ["356", "356(1)", "356(2)"],
        "triggers": [
            "defamation", "defames another", "making or publishing an imputation",
            "publicly defames another"
        ]
    },
    {
        "concept": "stalking",
        "statute": "BNS",
        "target_sections": ["78", "78(1)", "78(2)"],
        "triggers": [
            "stalking", "stalks", "repeatedly following a woman", "follows a woman despite disinterest",
            "repeatedly contact despite clear disinterest", "monitors the use by a woman of internet"
        ]
    },
    {
        "concept": "murder",
        "statute": "BNS",
        "target_sections": ["103", "103(1)"],
        "triggers": [
            "murder", "intentionally causing death", "punishment for murder",
            "causing a customer's death during a dispute", "intentionally caused the death",
            "caused the death of another", "intentionally caused the death of another"
        ]
    },
    {
        "concept": "attempt_murder",
        "statute": "BNS",
        "target_sections": ["109"],
        "triggers": [
            "attempt to murder", "attempts to kill another", "victim survived", "attempt to commit murder"
        ]
    },
    {
        "concept": "hurt",
        "statute": "BNS",
        "target_sections": ["115", "115(2)"],
        "triggers": [
            "voluntarily causing hurt", "non-fatal bodily injury without grievous", "causes hurt"
        ]
    },
    {
        "concept": "grievous_hurt",
        "statute": "BNS",
        "target_sections": ["117", "118"],
        "triggers": [
            "grievous hurt", "voluntarily causing grievous hurt", "dangerous weapon to cause hurt"
        ]
    },
    {
        "concept": "organised_crime",
        "statute": "BNS",
        "target_sections": ["111", "112"],
        "triggers": [
            "organised crime", "petty organised criminal activity", "syndicate"
        ]
    },
    {
        "concept": "terrorist_act",
        "statute": "BNS",
        "target_sections": ["113"],
        "triggers": [
            "terrorist act", "terrorist act as defined by the bns"
        ]
    },

    # --- CRIMINAL PROCEDURE & INVESTIGATION (BNSS / CrPC) ---
    {
        "concept": "police_remand",
        "statute": "BNSS",
        "target_sections": ["187", "187(2)"],
        "triggers": [
            "remand", "police custody", "detention during investigation", "custody period",
            "statutory remand mechanism"
        ]
    },
    {
        "concept": "arrest_without_warrant",
        "statute": "BNSS",
        "target_sections": ["35", "35(1)"],
        "triggers": [
            "arrest without a warrant", "arrest without warrant", "arrest powers and safeguards",
            "arrest is necessary", "arrest as automatic"
        ]
    },
    {
        "concept": "notice_of_appearance",
        "statute": "BNSS",
        "target_sections": ["35(3)"],
        "triggers": [
            "notice of appearance", "notice requiring a person to appear", "notice instead of arrest",
            "served a notice of appearance", "compliance with the notice mechanism"
        ]
    },
    {
        "concept": "bailable_bail",
        "statute": "BNSS",
        "target_sections": ["478"],
        "triggers": [
            "bailable offence", "bail in bailable", "bail is to be taken in certain cases",
            "released on bail in a bailable offence"
        ]
    },
    {
        "concept": "undertrial_bail",
        "statute": "BNSS",
        "target_sections": ["479", "479(1)"],
        "triggers": [
            "undertrial prisoner", "undertrial detention", "first-time offender", "spent a substantial portion",
            "release of an undertrial prisoner"
        ]
    },
    {
        "concept": "judgment_pronouncement",
        "statute": "BNSS",
        "target_sections": ["392", "392(1)"],
        "triggers": [
            "pronounce judgment", "judgment pronouncement", "statutory framework for pronouncement",
            "judgment in every trial"
        ]
    },
    {
        "concept": "fir_registration",
        "statute": "BNSS",
        "target_sections": ["173", "173(1)", "173(3)"],
        "triggers": [
            "information in cognizable cases", "fir", "e-fir", "zero fir", "registration of fir",
            "registration and investigation of a cognizable case", "information in cognizable cases",
            "information requiring consideration of registration"
        ]
    },
    {
        "concept": "search_audio_video",
        "statute": "BNSS",
        "target_sections": ["105"],
        "triggers": [
            "search and seizure through audio-video", "audio-video electronic means",
            "recorded through audio-video", "records the process through audio-video", "search of premises",
            "process can be recorded through audio-video"
        ]
    },
    {
        "concept": "police_seizure",
        "statute": "BNSS",
        "target_sections": ["106"],
        "triggers": [
            "police seizure powers", "seize certain property", "seize property believed to be connected",
            "police seizure of property", "seize property believed to be connected with an offence"
        ]
    },
    {
        "concept": "proclamation_absconding",
        "statute": "BNSS",
        "target_sections": ["84", "85", "86"],
        "triggers": [
            "proclamation for a person absconding", "absconds after process", "attaching property of a proclaimed person",
            "proclamation procedure"
        ]
    },
    {
        "concept": "witness_statement_confrontation",
        "statute": "BNSS",
        "target_sections": ["183", "180"],
        "triggers": [
            "witness's statement to police", "statement to police was reduced to writing",
            "confront the witness", "statement to police contains a significant omission",
            "omission amounts to contradiction", "contradict the witness at trial", "contradict the witness"
        ]
    },

    # --- LAW OF EVIDENCE (BSA / IEA) ---
    {
        "concept": "electronic_evidence_cert",
        "statute": "BSA",
        "target_sections": ["63", "61", "62"],
        "triggers": [
            "electronic records", "digital record", "cctv", "cctv footage", "screenshots of repeated messages",
            "admissibility of electronic records", "certificate for electronic record", "digital cctv",
            "computer-generated record", "screenshots", "electronic message", "smartphone", "smartphones",
            "laptop", "computer", "mobile phone", "messages", "electronic recording", "business records"
        ]
    },
    {
        "concept": "electronic_signature",
        "statute": "BSA",
        "target_sections": ["67A", "67"],
        "triggers": [
            "electronic signature", "digital signature", "electronic signature on a digital record",
            "proof as to an electronic signature"
        ]
    },
    {
        "concept": "attesting_witness",
        "statute": "BSA",
        "target_sections": ["67", "68", "69"],
        "triggers": [
            "attesting witness", "proof of execution of document", "document requires attestation",
            "cannot locate an attesting witness", "requires attestation", "required by law to be attested"
        ]
    },
    {
        "concept": "burden_of_proof",
        "statute": "BSA",
        "target_sections": ["104", "105", "106"],
        "triggers": [
            "burden of proof", "burden of proving fact", "onus of proving", "bears the burden",
            "especially within the knowledge"
        ]
    },
    {
        "concept": "public_record_entry",
        "statute": "BSA",
        "target_sections": ["29", "35"],
        "triggers": [
            "public servant's electronic record", "discharge of official duty", "entry in public record"
        ]
    },
    {
        "concept": "custody_statement_discovery",
        "statute": "BSA",
        "target_sections": ["23", "24"],
        "triggers": [
            "statement made by an accused while in police custody", "confession to police",
            "confession, police custody", "discovery of fact in custody", "admissible as a confession",
            "automatically admissible as a confession"
        ]
    },

    # --- SPECIAL CHILD PROTECTION STATUTE (POCSO ACT 2012) ---
    {
        "concept": "pocso_offences",
        "statute": "POCSO",
        "target_sections": ["3", "4", "5", "6", "7", "8", "9", "10"],
        "triggers": [
            "child victim", "15-year-old child", "child subjected to sexual", "penetrative sexual assault",
            "aggravated penetrative sexual assault", "sexual assault on child", "pocso", "child-protection",
            "child sexual offences"
        ]
    },
    {
        "concept": "pocso_reporting",
        "statute": "POCSO",
        "target_sections": ["19", "21"],
        "triggers": [
            "mandatory reporting of child sexual", "duty to report child sexual", "failure to report pocso"
        ]
    },
    {
        "concept": "pocso_special_court",
        "statute": "POCSO",
        "target_sections": ["28", "33"],
        "triggers": [
            "special court for child", "special court under pocso", "procedure of special court pocso"
        ]
    }
]

class LegalQueryAnalyzer:
    def __init__(self):
        pass

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query into detected legal concepts, candidate sections, and decomposed sub-intents."""
        q_lower = query.lower()
        matched_concepts = []
        candidate_statutes = set()
        candidate_sections = set()
        enriched_search_tokens = set()

        for mapping in CONCEPT_MAPPINGS:
            for trig in mapping["triggers"]:
                if trig in q_lower:
                    matched_concepts.append(mapping)
                    candidate_statutes.add(mapping["statute"])
                    for s in mapping["target_sections"]:
                        candidate_sections.add(s)
                    enriched_search_tokens.add(mapping["concept"])
                    break

        # Explicit target statute override when user specifically asks for that statute
        if "which bns provision" in q_lower or "under bns" in q_lower or "under the bns" in q_lower or "which bns " in q_lower:
            candidate_statutes = {"BNS"}
        elif "which bnss provision" in q_lower or "under bnss" in q_lower or "under the bnss" in q_lower or "which bnss " in q_lower:
            candidate_statutes = {"BNSS"}
        elif "which bsa provision" in q_lower or "under bsa" in q_lower or "under the bsa" in q_lower or "which bsa " in q_lower or "under the bsa?" in q_lower:
            candidate_statutes = {"BSA"}
        elif "which pocso provision" in q_lower or "under pocso" in q_lower or "under the pocso" in q_lower or "which pocso " in q_lower:
            candidate_statutes = {"POCSO"}
        else:
            # Check general cues
            if any(w in q_lower for w in ["bns", "bharatiya nyaya", "ipc", "theft", "extortion", "robbery", "murder", "forgery", "defamation", "stalking", "mischief", "cheating", "hurt"]):
                candidate_statutes.add("BNS")
            if any(w in q_lower for w in ["bnss", "bharatiya nagarik", "crpc", "arrest", "remand", "bail", "undertrial", "fir", "seizure", "proclamation", "investigation"]):
                candidate_statutes.add("BNSS")
            if any(w in q_lower for w in ["bsa", "bharatiya sakshya", "iea", "evidence", "cctv", "electronic", "certificate", "attesting", "burden of proof", "screenshot", "confession"]):
                candidate_statutes.add("BSA")
            if any(w in q_lower for w in ["pocso", "child victim", "15-year-old child", "child subjected", "sexual assault on child", "child-protection", "child"]):
                candidate_statutes.add("POCSO")
                candidate_statutes.add("BNS")

            # Three-tier criminal architecture inquiries
            if any(phrase in q_lower for phrase in ["three legal layers", "separated by legal function", "statutes should be separated", "three layers", "statutory stack", "same statute should supply", "provisions should be separated"]):
                candidate_statutes.add("BNS")
                candidate_statutes.add("BNSS")
                candidate_statutes.add("BSA")

        # Multi-statute query decomposition
        sub_intents = []
        is_multi = len(candidate_statutes) > 1
        
        if is_multi:
            for st in candidate_statutes:
                sub_intents.append({"statute": st, "sub_query": f"{st} provision for {query}"})
        else:
            single_st = list(candidate_statutes)[0] if candidate_statutes else "GENERAL"
            sub_intents.append({"statute": single_st, "sub_query": query})

        return {
            "query": query,
            "matched_concepts": [m["concept"] for m in matched_concepts],
            "candidate_statutes": list(candidate_statutes),
            "candidate_sections": list(candidate_sections),
            "enriched_tokens": list(enriched_search_tokens),
            "sub_intents": sub_intents,
            "is_multi_statute": is_multi
        }
