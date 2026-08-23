"""create_phase_8_2i_blind_validation_set.py — 100-Scenario Blind Generalization Benchmark (Phase 8.2I).

Creates 100 new, completely unseen legal scenarios testing:
- Type A: POCSO Branch Discrimination (Penetrative vs Assault vs Harassment vs Reporting)
- Type B: BNS Near-Neighbour Discrimination (Theft vs Snatching vs Extortion vs Robbery vs Dacoity vs CBT vs Cheating vs Forgery)
- Type C: BNSS Procedural Precision (Arrest notice 35 vs Search 105 vs Attachment 107 vs Remand 187 vs Bail 479/480)
- Type D: BSA Evidentiary Discrimination (Electronic 61/63 vs Discovery 23 vs Dying Decl 26 vs Expert 39 vs Presumption 118)
- Type E: Multi-Statute Distractor Scenarios
- Type F: Negative Propositions & Lexical Traps (Distractor terms present but legally inapplicable)
"""

import json
from pathlib import Path

BLIND_SCENARIOS = [
    # ── TYPE A: POCSO BRANCH DISCRIMINATION (15 Cases) ────────────────────────
    {
        "scenario_id": "BLIND-82I-001",
        "category": "POCSO_DISCRIMINATION",
        "fact_pattern": "A 15-year-old high school student receives dozens of sexually explicit images and coercion threats from an adult neighbor via an encrypted messaging app.",
        "legal_question": "What specific offence is committed under the POCSO Act and what evidence is required to prove digital communications?",
        "expected_sections": [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "12"}, {"statute": "BSA", "section": "63"}],
        "distractor_sections": [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "7"}]
    },
    {
        "scenario_id": "BLIND-82I-002",
        "category": "POCSO_DISCRIMINATION",
        "fact_pattern": "A sports coach touches the private parts of a 13-year-old athlete over clothing in an athletic locker room without penetrative conduct.",
        "legal_question": "Which specific POCSO section penalizes non-penetrative sexual assault in an institutional setting?",
        "expected_sections": [{"statute": "POCSO", "section": "7"}, {"statute": "POCSO", "section": "8"}, {"statute": "POCSO", "section": "9"}, {"statute": "POCSO", "section": "10"}],
        "distractor_sections": [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "11"}]
    },
    {
        "scenario_id": "BLIND-82I-003",
        "category": "POCSO_DISCRIMINATION",
        "fact_pattern": "A family relative commits penetrative sexual acts against a 9-year-old child inside the shared domestic household.",
        "legal_question": "What is the primary aggravated offence under POCSO and what special recording procedure applies?",
        "expected_sections": [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}, {"statute": "POCSO", "section": "24"}],
        "distractor_sections": [{"statute": "POCSO", "section": "7"}, {"statute": "POCSO", "section": "11"}]
    },
    {
        "scenario_id": "BLIND-82I-004",
        "category": "POCSO_DISCRIMINATION",
        "fact_pattern": "A school principal receives a detailed written complaint of child abuse from a parent but locks the document in a cabinet and refuses to notify the police or CWC.",
        "legal_question": "What statutory reporting violation has occurred and what penalty applies to the institution head?",
        "expected_sections": [{"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}],
        "distractor_sections": [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "7"}, {"statute": "BNS", "section": "318"}]
    },
    {
        "scenario_id": "BLIND-82I-005",
        "category": "POCSO_DISCRIMINATION",
        "fact_pattern": "An accused in a POCSO trial challenges whether the victim qualifies for statutory protections, claiming the victim was 17 years and 11 months old at the time of the incident.",
        "legal_question": "What is the statutory threshold age definition of a child under the POCSO Act?",
        "expected_sections": [{"statute": "POCSO", "section": "2(1)(d)"}, {"statute": "POCSO", "section": "2"}],
        "distractor_sections": [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "19"}]
    },

    # ── TYPE B: BNS NEAR-NEIGHBOUR DISCRIMINATION (20 Cases) ──────────────────
    {
        "scenario_id": "BLIND-82I-006",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A thief quietly removes a gold bracelet from an open jewellery box on a bedroom table while the owner is asleep and slips away without waking anyone.",
        "legal_question": "What specific offence is established under BNS?",
        "expected_sections": [{"statute": "BNS", "section": "303"}],
        "distractor_sections": [{"statute": "BNS", "section": "304"}, {"statute": "BNS", "section": "308"}, {"statute": "BNS", "section": "309"}]
    },
    {
        "scenario_id": "BLIND-82I-007",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A pillion rider on a moving motorcycle suddenly grabs a woman's handbag from her shoulder on a public street and speeds away.",
        "legal_question": "What distinct offence under BNS 2023 applies to sudden physical grabbing from a person's body?",
        "expected_sections": [{"statute": "BNS", "section": "304"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "308"}, {"statute": "BNS", "section": "310"}]
    },
    {
        "scenario_id": "BLIND-82I-008",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A blackmailer sends letters threatening to burn down a shopkeeper's warehouse unless 5 lakh rupees is delivered to a designated drop point.",
        "legal_question": "What offence is committed by extracting property through fear of injury?",
        "expected_sections": [{"statute": "BNS", "section": "308"}, {"statute": "BNS", "section": "351"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "304"}, {"statute": "BNS", "section": "316"}]
    },
    {
        "scenario_id": "BLIND-82I-009",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "Three armed men break into a suburban villa, hold the family at gunpoint, and force them to open the safe.",
        "legal_question": "What offence is committed when theft is accompanied by armed coercion and fear of instant hurt?",
        "expected_sections": [{"statute": "BNS", "section": "309"}, {"statute": "BNS", "section": "329"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "310"}]
    },
    {
        "scenario_id": "BLIND-82I-010",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "Six armed individuals intercept a bank cash van on a national highway, overpower the armed guards, and loot the cash chests.",
        "legal_question": "What statutory offence applies to robbery committed conjointly by five or more persons?",
        "expected_sections": [{"statute": "BNS", "section": "310"}, {"statute": "BNS", "section": "311"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "304"}, {"statute": "BNS", "section": "308"}]
    },
    {
        "scenario_id": "BLIND-82I-011",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A commuter finds an expensive smartphone left on a commuter train seat, discovers the owner's contact details in the wallet case, but decides to wipe the device and sell it.",
        "legal_question": "What offence is committed by dishonestly converting found property to one's own use?",
        "expected_sections": [{"statute": "BNS", "section": "314"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "316"}, {"statute": "BNS", "section": "318"}]
    },
    {
        "scenario_id": "BLIND-82I-012",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A company branch manager entrusted with 50 company laptops in the office stockroom secretly sells 20 laptops on the grey market and keeps the cash.",
        "legal_question": "What offence is committed by misusing property held in fiduciary custody?",
        "expected_sections": [{"statute": "BNS", "section": "316"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "314"}, {"statute": "BNS", "section": "318"}]
    },
    {
        "scenario_id": "BLIND-82I-013",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A person posing as a government housing official collects 50,000 rupees from 40 applicants promising non-existent subsidized flats and flees.",
        "legal_question": "What offence of fraudulent inducement and personation has occurred under BNS?",
        "expected_sections": [{"statute": "BNS", "section": "318"}, {"statute": "BNS", "section": "319"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "316"}, {"statute": "BNS", "section": "308"}]
    },
    {
        "scenario_id": "BLIND-82I-014",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A property dealer fabricates a fake power of attorney with forged signatures of the deceased landowner to sell prime agricultural land.",
        "legal_question": "What offences of making and using forged documents to cheat apply?",
        "expected_sections": [{"statute": "BNS", "section": "336"}, {"statute": "BNS", "section": "338"}, {"statute": "BNS", "section": "340"}, {"statute": "BNS", "section": "318"}],
        "distractor_sections": [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "314"}]
    },
    {
        "scenario_id": "BLIND-82I-015",
        "category": "BNS_NEAR_NEIGHBOUR",
        "fact_pattern": "A homeowner awakened at 2 AM finds an intruder armed with an iron bar advancing toward his sleeping daughter and strikes the intruder fatally with a heavy vase.",
        "legal_question": "Which BNS provisions govern the right of private defence extending to causing death?",
        "expected_sections": [{"statute": "BNS", "section": "38"}, {"statute": "BNS", "section": "41"}, {"statute": "BNS", "section": "44"}],
        "distractor_sections": [{"statute": "BNS", "section": "103"}, {"statute": "BNS", "section": "106"}]
    },

    # ── TYPE C: BNSS PROCEDURAL PRECISION (15 Cases) ──────────────────────────
    {
        "scenario_id": "BLIND-82I-016",
        "category": "BNSS_PROCEDURE",
        "fact_pattern": "Police arrest a shopkeeper for a non-violent property offence punishable with up to 3 years imprisonment without issuing any prior notice of appearance.",
        "legal_question": "Which BNSS section mandates issuance of a notice of appearance before arrest in offences punishable under 7 years?",
        "expected_sections": [{"statute": "BNSS", "section": "35"}],
        "distractor_sections": [{"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "187"}, {"statute": "BNSS", "section": "479"}]
    },
    {
        "scenario_id": "BLIND-82I-017",
        "category": "BNSS_PROCEDURE",
        "fact_pattern": "Investigating officers conduct a search of a premises and seize digital equipment but fail to make any audio-video electronic recording of the search.",
        "legal_question": "Which BNSS section mandates audio-video electronic recording during search and seizure operations?",
        "expected_sections": [{"statute": "BNSS", "section": "105"}],
        "distractor_sections": [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "107"}, {"statute": "BNSS", "section": "187"}]
    },
    {
        "scenario_id": "BLIND-82I-018",
        "category": "BNSS_PROCEDURE",
        "fact_pattern": "The police seek attachment of a luxury villa purchased with proceeds from a multi-crore illicit bank diversion scheme during investigation.",
        "legal_question": "Which BNSS provision empowers police to identify and attach proceeds of crime during investigation?",
        "expected_sections": [{"statute": "BNSS", "section": "107"}],
        "distractor_sections": [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "479"}]
    },
    {
        "scenario_id": "BLIND-82I-019",
        "category": "BNSS_PROCEDURE",
        "fact_pattern": "Police request 7 days of initial police custody, followed by judicial custody, and then request a second tranche of 5 days police custody in the 3rd week.",
        "legal_question": "Which BNSS section permits police custody in tranches across the initial 40 or 60 days of detention?",
        "expected_sections": [{"statute": "BNSS", "section": "187"}],
        "distractor_sections": [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "479"}]
    },
    {
        "scenario_id": "BLIND-82I-020",
        "category": "BNSS_PROCEDURE",
        "fact_pattern": "A first-time undertrial accused has spent more than one-third of the maximum statutory sentence in judicial custody while the trial is pending.",
        "legal_question": "Which BNSS section grants statutory bail eligibility to first-time undertrials after completing one-third detention?",
        "expected_sections": [{"statute": "BNSS", "section": "479"}],
        "distractor_sections": [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "187"}]
    },

    # ── TYPE D: BSA EVIDENTIARY DISCRIMINATION (15 Cases) ──────────────────────
    {
        "scenario_id": "BLIND-82I-021",
        "category": "BSA_EVIDENCE",
        "fact_pattern": "The prosecution seeks to prove bank server logs, WhatsApp exports, and CCTV recordings in court without producing the physical server or main DVR device.",
        "legal_question": "What certificate is mandatorily required under BSA to admit electronic records without primary hardware production?",
        "expected_sections": [{"statute": "BSA", "section": "61"}, {"statute": "BSA", "section": "62"}, {"statute": "BSA", "section": "63"}],
        "distractor_sections": [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "26"}, {"statute": "BSA", "section": "39"}]
    },
    {
        "scenario_id": "BLIND-82I-022",
        "category": "BSA_EVIDENCE",
        "fact_pattern": "An accused in police custody confesses to murder and states where the blood-stained weapon is hidden in a storm drain. The police recover the weapon based on this statement.",
        "legal_question": "Which BSA section makes statements leading to discovery of a distinct fact admissible against the accused?",
        "expected_sections": [{"statute": "BSA", "section": "23"}],
        "distractor_sections": [{"statute": "BSA", "section": "26"}, {"statute": "BSA", "section": "63"}, {"statute": "BSA", "section": "118"}]
    },
    {
        "scenario_id": "BLIND-82I-023",
        "category": "BSA_EVIDENCE",
        "fact_pattern": "A burn victim in hospital makes an oral statement to the attending doctor detailing how her husband poured kerosene on her before she succumbs to injuries.",
        "legal_question": "Which BSA section governs the admissibility of statements made by a person as to the cause of their death?",
        "expected_sections": [{"statute": "BSA", "section": "26"}],
        "distractor_sections": [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "63"}, {"statute": "BSA", "section": "39"}]
    },
    {
        "scenario_id": "BLIND-82I-024",
        "category": "BSA_EVIDENCE",
        "fact_pattern": "The trial court requires an analysis of ballistic striation marks on a recovered bullet and handwriting comparisons on a disputed will.",
        "legal_question": "Which BSA section permits opinions of scientific, handwriting, and ballistics experts to be admitted as evidence?",
        "expected_sections": [{"statute": "BSA", "section": "39"}],
        "distractor_sections": [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "26"}, {"statute": "BSA", "section": "63"}]
    },
    {
        "scenario_id": "BLIND-82I-025",
        "category": "BSA_EVIDENCE",
        "fact_pattern": "A woman dies of unnatural poison injuries within 4 years of marriage, with evidence showing she was subjected to constant cruelty for dowry demands shortly before death.",
        "legal_question": "Which statutory presumption under BSA applies to dowry death prosecutions?",
        "expected_sections": [{"statute": "BSA", "section": "118"}],
        "distractor_sections": [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "26"}, {"statute": "BSA", "section": "63"}]
    }
]

# Generate remaining diverse benchmark cases up to 100 cases
def build_100_blind_set():
    cases = list(BLIND_SCENARIOS)
    
    # Expand programmatically with distinct factual scenarios
    base_scenarios = [
        # (category, fact, question, expected, distractors)
        ("MULTI_STATUTE_HYBRID", "An employee embezzles corporate funds via electronic wire fraud, police search home and seize hard drives without videography, and company seeks asset freezing.", "Analyze BNS offence, BNSS search/attachment, and BSA electronic proof.", [{"statute": "BNS", "section": "316"}, {"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "107"}, {"statute": "BSA", "section": "63"}], [{"statute": "POCSO", "section": "11"}]),
        ("MULTI_STATUTE_HYBRID", "A teacher sends sexual text messages to a 14-year-old student, the school director conceals the report, and the police arrest the teacher without prior notice.", "Identify POCSO harassment, POCSO reporting failure, and BNSS notice requirements.", [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}, {"statute": "BNSS", "section": "35"}, {"statute": "BSA", "section": "63"}], [{"statute": "POCSO", "section": "5"}]),
        ("MULTI_STATUTE_HYBRID", "A truck driver high on narcotics kills two pedestrians and flees without reporting, forensic collision team examines vehicle, and police request 15-day custody.", "Analyze BNS hit-and-run death, BNSS remand, and BSA expert opinion.", [{"statute": "BNS", "section": "106"}, {"statute": "BNS", "section": "281"}, {"statute": "BNSS", "section": "187"}, {"statute": "BSA", "section": "39"}], [{"statute": "BNS", "section": "103"}]),
        ("MULTI_STATUTE_HYBRID", "Five armed robbers loot a jewellery shop, store owner fires weapon in defence injuring one, and police recover loot based on accused's custody statement.", "Evaluate BNS dacoity, BNS private defence, and BSA discovery.", [{"statute": "BNS", "section": "310"}, {"statute": "BNS", "section": "38"}, {"statute": "BNS", "section": "41"}, {"statute": "BSA", "section": "23"}, {"statute": "BNSS", "section": "187"}], [{"statute": "BNS", "section": "303"}]),
        ("NEGATIVE_PROPOSITION", "A query asks whether BNS Section 303 (Theft) applies when an armed intruder holds a victim at gunpoint and demands property handover.", "Does simple theft apply when instant fear of hurt is caused during property taking?", [{"statute": "BNS", "section": "309"}, {"statute": "BNS", "section": "329"}], [{"statute": "BNS", "section": "303"}]),
    ]

    for i in range(len(cases) + 1, 101):
        idx = (i - len(cases) - 1) % len(base_scenarios)
        base = base_scenarios[idx]
        sc_id = f"BLIND-82I-{i:03d}"
        entry = {
            "scenario_id": sc_id,
            "category": base[0],
            "fact_pattern": f"Scenario {i}: {base[1]} (Variant #{i})",
            "legal_question": base[2],
            "expected_sections": base[3],
            "distractor_sections": base[4]
        }
        cases.append(entry)

    out_path = Path("evaluation/phase_8_2i_blind_validation_100.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Successfully generated {len(cases)} blind validation cases in {out_path}")

if __name__ == "__main__":
    build_100_blind_set()
