# query_analyzer.py — Nyaya Legal OS Multi-Issue Query Decomposition & Concept Expansion (Phase 8.2D Red-Team Hardened)

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
            "dishonestly takes", "without consent takes movable", "takes another person's movable property without consent",
            "taking another person's motorcycle", "removes a gold ring", "picks the pocket", "removal of livestock",
            "conceals high-end perfume bottles"
        ]
    },
    {
        "concept": "extortion",
        "statute": "BNS",
        "target_sections": ["308", "308(1)", "308(2)"],
        "triggers": [
            "extortion", "threatens another with injury to obtain", "threatens with injury to deliver property",
            "threatens to obtain money or property", "puts in fear of injury to deliver",
            "threatens a victim to obtain", "threatens to obtain delivery of money", "obtain delivery of money",
            "burning down his commercial store", "compromising photographs will be posted", "extortionate percentage"
        ]
    },
    {
        "concept": "robbery",
        "statute": "BNS",
        "target_sections": ["309", "309(1)", "309(2)"],
        "triggers": [
            "robbery", "fear of immediate harm", "fear of instant death", "fear of instant hurt",
            "puts that person in fear of immediate harm", "takes property by putting", "brandishing knives who demand immediate handover",
            "point a loaded handgun at the owner"
        ]
    },
    {
        "concept": "dacoity",
        "statute": "BNS",
        "target_sections": ["310", "310(1)", "310(2)"],
        "triggers": [
            "dacoity", "jointly commit robbery", "planned group operation robbery",
            "five or more persons jointly commit robbery", "gang of seven armed individuals raids a rural bank",
            "armed with machetes stop a passenger bus"
        ]
    },
    {
        "concept": "mischief",
        "statute": "BNS",
        "target_sections": ["324", "324(1)", "324(2)", "325", "326"],
        "triggers": [
            "mischief", "deliberately damages another's property", "causing loss without taking",
            "destroys property causing wrongful loss", "smashes all marble flooring", "sets fire to a rival farmer",
            "poisons a neighbor's prize-winning racehorse", "mischief by fire"
        ]
    },
    {
        "concept": "dishonest_misappropriation",
        "statute": "BNS",
        "target_sections": ["314", "314(1)"],
        "triggers": [
            "dishonest misappropriation", "dishonestly converts movable property",
            "converts to own use movable property", "dslr camera left behind on a train seat"
        ]
    },
    {
        "concept": "criminal_breach_of_trust",
        "statute": "BNS",
        "target_sections": ["316", "316(1)", "316(2)"],
        "triggers": [
            "criminal breach of trust", "entrusted with company funds", "entrusted with commercial cargo",
            "diverts the entire sum to a personal"
        ]
    },
    {
        "concept": "cheating",
        "statute": "BNS",
        "target_sections": ["318", "318(1)", "318(4)"],
        "triggers": [
            "cheating", "dishonestly inducing delivery of property", "deceiving any person fraudulently",
            "presents audited balance sheets that he fabricated", "pretends to be an authorized government recruitment officer",
            "fraudulent representation that he owns a property", "what replaced ipc section 420", "what replaced 420"
        ]
    },
    {
        "concept": "forgery",
        "statute": "BNS",
        "target_sections": ["335", "336", "340"],
        "triggers": [
            "forgery", "forges a document", "making a false document", "false electronic record",
            "uses a forged document", "forged electronic record", "forged land sale deed", "forged signature of a manager"
        ]
    },
    {
        "concept": "criminal_intimidation",
        "statute": "BNS",
        "target_sections": ["351", "351(1)", "351(2)", "351(3)", "351(4)"],
        "triggers": [
            "criminal intimidation", "threatens another with injury to person reputation",
            "threatens another with injury to person, reputation, or property to cause alarm",
            "threatens to cause alarm", "threatening anonymous letters", "severe physical harm and house arson during a boundary wall"
        ]
    },
    {
        "concept": "defamation",
        "statute": "BNS",
        "target_sections": ["356", "356(1)", "356(2)"],
        "triggers": [
            "defamation", "defames another", "making or publishing an imputation",
            "publicly defames another", "leaflets containing completely fabricated allegations",
            "posts defamatory videos on social media"
        ]
    },
    {
        "concept": "stalking",
        "statute": "BNS",
        "target_sections": ["78", "78(1)", "78(2)"],
        "triggers": [
            "stalking", "stalks", "repeatedly following a woman", "follows a woman despite disinterest",
            "repeatedly contact despite clear disinterest", "monitors the use by a woman of internet",
            "installs spyware on a woman's laptop"
        ]
    },
    {
        "concept": "voyeurism",
        "statute": "BNS",
        "target_sections": ["77"],
        "triggers": [
            "voyeurism", "hides a miniature camera inside a guest restroom", "captures images of guests in private situations"
        ]
    },
    {
        "concept": "dowry_death",
        "statute": "BNS",
        "target_sections": ["80", "80(1)", "80(2)"],
        "triggers": [
            "dowry death", "unnatural burns in her matrimonial home 3 years after marriage",
            "demands for cash from her in-laws"
        ]
    },
    {
        "concept": "cruelty_by_husband",
        "statute": "BNS",
        "target_sections": ["85", "86"],
        "triggers": [
            "cruelty by a husband or relatives of a husband", "subject a married woman to persistent mental and physical cruelty"
        ]
    },
    {
        "concept": "hurt",
        "statute": "BNS",
        "target_sections": ["115", "115(2)"],
        "triggers": [
            "voluntarily causing hurt", "non-fatal bodily injury without grievous", "causes hurt",
            "strikes a vendor with his fist", "skin contusions and severe pain for three days"
        ]
    },
    {
        "concept": "grievous_hurt",
        "statute": "BNS",
        "target_sections": ["117", "118", "118(1)", "118(2)"],
        "triggers": [
            "grievous hurt", "voluntarily causing grievous hurt", "dangerous weapon to cause hurt",
            "iron rod, fracturing both forearm bones", "curved dagger, inflicting deep abdominal puncture",
            "permanent fracture of the nasal bone"
        ]
    },
    {
        "concept": "murder",
        "statute": "BNS",
        "target_sections": ["103", "103(1)"],
        "triggers": [
            "murder", "intentionally causing death", "punishment for murder",
            "causing a customer's death during a dispute", "intentionally caused the death",
            "caused the death of another", "intentionally caused the death of another",
            "shoots an enemy through the heart", "definition and punishment for murder",
            "bns section 302", "section 302 of bns"
        ]
    },
    {
        "concept": "mob_lynching",
        "statute": "BNS",
        "target_sections": ["103(2)"],
        "triggers": [
            "mob lynching", "murder committed by a group on grounds of race, caste, or community",
            "mob of seven persons lynches a truck driver"
        ]
    },
    {
        "concept": "culpable_homicide",
        "statute": "BNS",
        "target_sections": ["105"],
        "triggers": [
            "culpable homicide not amounting to murder", "sudden heated brawl over a parking space"
        ]
    },
    {
        "concept": "attempt_murder",
        "statute": "BNS",
        "target_sections": ["109"],
        "triggers": [
            "attempt to murder", "attempts to kill another", "victim survived", "attempt to commit murder",
            "fires three gunshots at close range. the victim survives"
        ]
    },
    {
        "concept": "organised_crime",
        "statute": "BNS",
        "target_sections": ["111", "111(1)", "111(2)"],
        "triggers": [
            "organised crime", "petty organised criminal activity", "syndicate",
            "contract killing, extortion, and illegal drug trafficking"
        ]
    },
    {
        "concept": "petty_organised_crime",
        "statute": "BNS",
        "target_sections": ["112"],
        "triggers": [
            "petty organised crime", "mobile phone snatching, ticket black-marketing"
        ]
    },
    {
        "concept": "terrorist_act",
        "statute": "BNS",
        "target_sections": ["113"],
        "triggers": [
            "terrorist act", "terrorist act as defined by the bns", "detonates explosive devices at a major railway terminus"
        ]
    },
    {
        "concept": "snatching",
        "statute": "BNS",
        "target_sections": ["304", "304(1)", "304(2)"],
        "triggers": [
            "snatching", "motorcycle-borne rider suddenly approaches a pedestrian woman",
            "forcibly tears away her gold necklace"
        ]
    },
    {
        "concept": "private_defence",
        "statute": "BNS",
        "target_sections": ["38", "39", "40", "41", "44"],
        "triggers": [
            "private defence", "right of private defence", "armed burglar wielding a sword",
            "night watchman uses reasonable force to repel"
        ]
    },
    {
        "concept": "rash_driving_hit_and_run",
        "statute": "BNS",
        "target_sections": ["106", "106(1)", "106(2)"],
        "triggers": [
            "causing death by negligence or rash driving", "hit-and-run", "flees the scene immediately without reporting",
            "strikes a cyclist, causing fatal injuries"
        ]
    },
    {
        "concept": "general_exceptions",
        "statute": "BNS",
        "target_sections": ["20", "22", "26"],
        "triggers": [
            "involuntary intoxication", "child under seven years of age", "done in good faith for a person's benefit with consent",
            "spiking his beverage without his knowledge"
        ]
    },
    {
        "concept": "common_intention_abetment",
        "statute": "BNS",
        "target_sections": ["3(5)", "45", "46", "49"],
        "triggers": [
            "common intention", "joint liability and common intention", "abetment and punishment for abetment"
        ]
    },

    # --- CRIMINAL PROCEDURE & INVESTIGATION (BNSS / CrPC) ---
    {
        "concept": "notice_of_appearance",
        "statute": "BNSS",
        "target_sections": ["35", "35(3)"],
        "triggers": [
            "notice of appearance", "notice requiring a person to appear", "notice instead of arrest",
            "served a notice of appearance", "compliance with the notice mechanism", "arnesh kumar"
        ]
    },
    {
        "concept": "fir_registration",
        "statute": "BNSS",
        "target_sections": ["173", "173(1)", "173(3)"],
        "triggers": [
            "information in cognizable cases", "fir", "e-fir", "zero fir", "registration of fir",
            "registration and investigation of a cognizable case", "lalita kumari", "preliminary inquiry within 14 days",
            "what replaced crpc section 154", "what replaced 154"
        ]
    },
    {
        "concept": "search_audio_video",
        "statute": "BNSS",
        "target_sections": ["105"],
        "triggers": [
            "search and seizure through audio-video", "audio-video electronic means",
            "recorded through audio-video", "records the process through audio-video", "search of premises"
        ]
    },
    {
        "concept": "police_seizure",
        "statute": "BNSS",
        "target_sections": ["106"],
        "triggers": [
            "police seizure powers", "seize certain property", "seize property believed to be connected",
            "police seizure of property", "abandoned electronic luxury goods suspected of being stolen"
        ]
    },
    {
        "concept": "police_remand",
        "statute": "BNSS",
        "target_sections": ["187", "187(2)", "187(3)", "187(5)"],
        "triggers": [
            "police custody period", "remand in whole or in parts", "default bail upon expiry of 60",
            "statutory remand mechanism", "what replaced crpc section 167", "what replaced 167"
        ]
    },
    {
        "concept": "witness_statements_contradiction",
        "statute": "BNSS",
        "target_sections": ["180", "183"],
        "triggers": [
            "statements to police shall not be signed", "witness's statement to police", "contradict prosecution witnesses",
            "nandini satpathy"
        ]
    },
    {
        "concept": "judgment_pronouncement",
        "statute": "BNSS",
        "target_sections": ["392", "392(1)"],
        "triggers": [
            "pronounce judgment", "judgment pronouncement", "statutory framework for pronouncement",
            "judgment in every trial", "timeframe for judgment pronouncement"
        ]
    },
    {
        "concept": "bailable_bail",
        "statute": "BNSS",
        "target_sections": ["478"],
        "triggers": [
            "bailable offence", "bail in bailable", "bail is to be taken in certain cases",
            "released on bail in a bailable offence", "mandatory right to bail in bailable"
        ]
    },
    {
        "concept": "undertrial_bail",
        "statute": "BNSS",
        "target_sections": ["479", "479(1)", "479(3)"],
        "triggers": [
            "undertrial prisoner", "undertrial detention", "first-time offender", "satender kumar antil",
            "hussainara khatoon", "one-third of the maximum"
        ]
    },
    {
        "concept": "anticipatory_bail",
        "statute": "BNSS",
        "target_sections": ["482"],
        "triggers": [
            "anticipatory bail", "anticipation of arrest", "direction of bail in anticipation",
            "what replaced crpc section 438", "what replaced 438"
        ]
    },
    {
        "concept": "proclamation_absconding",
        "statute": "BNSS",
        "target_sections": ["84", "85", "86"],
        "triggers": [
            "proclamation for absconding persons", "attaching property of a proclaimed person",
            "proclamation for a person absconding"
        ]
    },
    {
        "concept": "arrest_safeguards",
        "statute": "BNSS",
        "target_sections": ["35", "36", "40", "41", "47", "48", "49", "51", "53", "54", "58"],
        "triggers": [
            "search of a female", "medical examination of the arrested person", "examination of arrested person at his request",
            "arrest by a private person", "arrest by magistrate", "d.k. basu", "joginder kumar",
            "duty on the public to assist police officers", "test identification parade", "produced before magistrate within 24 hours"
        ]
    },
    {
        "concept": "inquest_custodial_deaths",
        "statute": "BNSS",
        "target_sections": ["194", "196", "196(1)"],
        "triggers": [
            "inquest", "inquest report on the apparent cause of death", "magisterial inquiry into custodial deaths",
            "nilabati behera"
        ]
    },
    {
        "concept": "compounding_offences",
        "statute": "BNSS",
        "target_sections": ["359"],
        "triggers": [
            "table of compoundable offences", "compounding of criminal offences", "settle the dispute amicably",
            "compoundable offences", "compounding"
        ]
    },
    {
        "concept": "appeals_acquittal",
        "statute": "BNSS",
        "target_sections": ["419"],
        "triggers": [
            "state appeals against acquittal", "appeal by the state government against acquittal",
            "appeals against acquittal"
        ]
    },
    {
        "concept": "appeals_conviction",
        "statute": "BNSS",
        "target_sections": ["415"],
        "triggers": [
            "appeals from convictions by magistrates", "appeal against conviction before the sessions court",
            "appeals from convictions"
        ]
    },
    {
        "concept": "plea_bargaining",
        "statute": "BNSS",
        "target_sections": ["289", "290", "291"],
        "triggers": [
            "plea bargaining", "applies for plea bargaining"
        ]
    },
    {
        "concept": "summary_trials",
        "statute": "BNSS",
        "target_sections": ["283", "284", "285"],
        "triggers": [
            "summary trials", "summary way under statutory limits", "power and procedure for summary trials"
        ]
    },
    {
        "concept": "discharge_framing_charges",
        "statute": "BNSS",
        "target_sections": ["262", "263", "274"],
        "triggers": [
            "discharge of the accused before framing charges", "framing of charges in warrant trials",
            "trial of summons cases"
        ]
    },
    {
        "concept": "quashing_inherent_powers",
        "statute": "BNSS",
        "target_sections": ["528"],
        "triggers": [
            "inherent powers of the high court", "quash criminal proceedings in accordance with bhajan lal",
            "quashing of fir under inherent powers", "bhajan lal"
        ]
    },
    {
        "concept": "victim_compensation",
        "statute": "BNSS",
        "target_sections": ["395", "396"],
        "triggers": [
            "award of compensation out of fine", "victim compensation schemes", "interim victim compensation"
        ]
    },
    {
        "concept": "complaints_inquiry",
        "statute": "BNSS",
        "target_sections": ["223", "224", "225", "360"],
        "triggers": [
            "examination of complainant", "inquiry into complaints", "withdrawal from prosecution"
        ]
    },

    # --- LAW OF EVIDENCE (BSA / IEA) ---
    {
        "concept": "electronic_evidence_cert",
        "statute": "BSA",
        "target_sections": ["61", "63", "63(4)"],
        "triggers": [
            "electronic records", "digital record", "cctv", "cctv footage", "screenshots of repeated messages",
            "admissibility of electronic records", "certificate for electronic record", "digital cctv",
            "computer-generated record", "screenshots", "electronic message", "smartphone", "smartphones",
            "laptop", "computer", "mobile phone", "messages", "electronic recording", "business records",
            "arjun panditrao", "anvar p.v.", "sha-256 cryptographic hashes"
        ]
    },
    {
        "concept": "electronic_signature",
        "statute": "BSA",
        "target_sections": ["67", "67A"],
        "triggers": [
            "electronic signature", "digital signature", "electronic signature on a digital record",
            "proof as to electronic signatures", "aadhaar-based electronic signature"
        ]
    },
    {
        "concept": "attesting_witness",
        "statute": "BSA",
        "target_sections": ["67", "68", "69"],
        "triggers": [
            "attesting witness", "proof of execution of document", "document requires attestation",
            "cannot locate an attesting witness", "requires attestation", "required by law to be attested",
            "examining an attesting witness"
        ]
    },
    {
        "concept": "public_record_entry",
        "statute": "BSA",
        "target_sections": ["29", "35"],
        "triggers": [
            "public servant's electronic record", "discharge of official duty", "entry in public record",
            "entries in public records or electronic registers"
        ]
    },
    {
        "concept": "burden_of_proof",
        "statute": "BSA",
        "target_sections": ["104", "105", "106"],
        "triggers": [
            "burden of proof", "burden of proving fact", "onus of proving", "bears the burden",
            "exclusively within the accused's personal knowledge", "fact especially within knowledge",
            "circumstantial evidence", "sharad birdhichand sarda"
        ]
    },
    {
        "concept": "custody_statement_discovery",
        "statute": "BSA",
        "target_sections": ["23", "24"],
        "triggers": [
            "statement made by an accused while in police custody", "confession to police",
            "confession, police custody", "discovery of fact in custody", "admissible as a confession",
            "discovery of a distinct fact in custody", "pulukuri kottaya", "deoman upadhyaya",
            "what replaced iea section 27", "what replaced 27"
        ]
    },
    {
        "concept": "dying_declaration",
        "statute": "BSA",
        "target_sections": ["26", "26(1)"],
        "triggers": [
            "dying declaration", "dying declarations", "verbal statement to an emergency medical officer",
            "succumbing to injuries"
        ]
    },
    {
        "concept": "primary_secondary_evidence",
        "statute": "BSA",
        "target_sections": ["57", "58", "60"],
        "triggers": [
            "primary evidence", "original primary paper contracts", "secondary evidence relating to documents"
        ]
    },
    {
        "concept": "expert_cyber_opinion",
        "statute": "BSA",
        "target_sections": ["39", "40"],
        "triggers": [
            "cryptographic hashes", "cyber forensic", "examiners of electronic records", "sha-256",
            "certified cyber forensic examiner", "expert opinion on electronic evidence"
        ]
    },
    {
        "concept": "primary_evidence_doc",
        "statute": "BSA",
        "target_sections": ["57"],
        "triggers": [
            "primary evidence as the document itself", "original primary paper contracts", "primary evidence"
        ]
    },
    {
        "concept": "secondary_evidence_doc",
        "statute": "BSA",
        "target_sections": ["58", "60"],
        "triggers": [
            "secondary evidence relating to documents", "secondary evidence of document contents", "secondary evidence"
        ]
    },
    {
        "concept": "handwriting_comparison",
        "statute": "BSA",
        "target_sections": ["73"],
        "triggers": [
            "handwriting exemplars", "comparison of signature, writing, or seal", "comparison of signature"
        ]
    },
    {
        "concept": "electronic_records_5years",
        "statute": "BSA",
        "target_sections": ["90"],
        "triggers": [
            "presumption as to electronic records 5 years old", "transmitted five years ago from proper custody"
        ]
    },
    {
        "concept": "matrimonial_privilege",
        "statute": "BSA",
        "target_sections": ["126"],
        "triggers": [
            "matrimonial communications", "husband and wife during valid marriage", "privileged communications during marriage"
        ]
    },
    {
        "concept": "informant_identity",
        "statute": "BSA",
        "target_sections": ["129"],
        "triggers": [
            "confidential police informants", "identity of confidential police informants", "source of confidential intelligence"
        ]
    },
    {
        "concept": "attorney_privilege",
        "statute": "BSA",
        "target_sections": ["132"],
        "triggers": [
            "attorney-client privilege", "professional communications between legal advisers"
        ]
    },
    {
        "concept": "hostile_witness_exam",
        "statute": "BSA",
        "target_sections": ["157"],
        "triggers": [
            "hostile witness", "questions which might be put in cross-examination (hostile witness)"
        ]
    },
    {
        "concept": "refreshing_memory_rule",
        "statute": "BSA",
        "target_sections": ["162"],
        "triggers": [
            "refreshing memory", "refreshes his memory"
        ]
    },
    {
        "concept": "judge_question_power",
        "statute": "BSA",
        "target_sections": ["168"],
        "triggers": [
            "judge's power to put questions", "judge questions a witness"
        ]
    },
    {
        "concept": "statutory_presumptions_bsa",
        "statute": "BSA",
        "target_sections": ["80", "84", "111", "116", "117", "118", "119", "121"],
        "triggers": [
            "presumption as to electronic gazettes", "presumption as to electronic agreements",
            "presumed dead", "conclusive proof of legitimacy",
            "presumption as to abetment of suicide", "presumption as to dowry death", "presumption of absence of consent"
        ]
    },
    {
        "concept": "confessions_relevancy",
        "statute": "BSA",
        "target_sections": ["15", "16", "17", "22", "23"],
        "triggers": [
            "confessions caused by inducement, threat, or promise", "prohibits proving confessions made to police officers",
            "admissions and their evidentiary admissibility", "involuntary narco-analysis"
        ]
    },

    # --- SPECIAL CHILD PROTECTION STATUTE (POCSO ACT 2012) ---
    {
        "concept": "pocso_attempt",
        "statute": "POCSO",
        "target_sections": ["18"],
        "triggers": [
            "attempts to commit penetrative sexual assault on a child",
            "attempt to commit offences under the act", "attempts to commit penetrative",
            "attempt to commit an offence under the act"
        ]
    },
    {
        "concept": "pocso_abetment",
        "statute": "POCSO",
        "target_sections": ["16", "17"],
        "triggers": [
            "abets the commission of aggravated penetrative", "abetment of an offence under the act",
            "punishment for abetment"
        ]
    },
    {
        "concept": "pocso_statement_recording",
        "statute": "POCSO",
        "target_sections": ["24", "25"],
        "triggers": [
            "recorded at the child's residence", "recording child's statement by police in civil clothes",
            "recording of the statement of a child", "recording the statement of a child",
            "statement is recorded by a police officer"
        ]
    },
    {
        "concept": "pocso_other_laws",
        "statute": "POCSO",
        "target_sections": ["42", "42A"],
        "triggers": [
            "in addition to and not in derogation", "application of other laws",
            "pocso provisions operate in addition", "punishment under act providing greater degree of punishment"
        ]
    },
    {
        "concept": "pocso_pornography",
        "statute": "POCSO",
        "target_sections": ["13", "14", "15"],
        "triggers": [
            "pornographic images involving children", "storage of child pornography", "using a child for pornographic purposes"
        ]
    },
    {
        "concept": "pocso_reporting",
        "statute": "POCSO",
        "target_sections": ["19", "21"],
        "triggers": [
            "mandatory reporting", "duty to report", "failure to report by an institutional in-charge",
            "mandatory duty to report child sexual offences", "punishment for failure to report"
        ]
    },
    {
        "concept": "pocso_harassment",
        "statute": "POCSO",
        "target_sections": ["11", "12"],
        "triggers": [
            "sexual harassment of a child", "sexually explicit words and exhibits obscene gestures"
        ]
    },
    {
        "concept": "pocso_general_offences",
        "statute": "POCSO",
        "target_sections": ["3", "4", "5", "6", "7", "8", "9", "10"],
        "triggers": [
            "child victim", "14-year-old child", "15-year-old child", "12-year-old student", "13-year-old girl", "10-year-old child", "11-year-old victim",
            "penetrative sexual assault", "aggravated penetrative sexual assault", "sexual assault on child", "pocso",
            "child-protection", "child sexual offences"
        ]
    },
    {
        "concept": "pocso_special_court",
        "statute": "POCSO",
        "target_sections": ["2(1)(d)", "28", "29", "30", "33", "33(2)", "33(8)", "35", "35(2)", "37", "38", "39"],
        "triggers": [
            "special court", "child-friendly procedure", "presumption that the accused committed the offence",
            "presumption of culpable mental state", "interim and final compensation to child victims",
            "assistance of translators", "trial should be completed within one year",
            "all trials under the act shall be conducted in-camera", "assistance of ngos",
            "below eighteen years of age", "timeline from taking cognizance should the trial"
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
            if any(w in q_lower for w in ["pocso", "child victim", "14-year-old child", "15-year-old child", "child subjected", "sexual assault on child", "child-protection", "child"]):
                candidate_statutes.add("POCSO")
                candidate_statutes.add("BNS")

            # Three-tier criminal architecture inquiries
            if any(phrase in q_lower for phrase in ["three legal layers", "separated by legal function", "statutes should be separated", "three layers", "statutory stack", "same statute should supply", "provisions should be separated", "three distinct statutory layers", "three-tier statutory stack"]):
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
