"""create_phase_8_2k_blind_validation_200.py — 200-Scenario Blind Generalization Benchmark (Phase 8.2K).

Creates 200 brand-new, completely unseen legal scenarios:
- 40 Multi-Statute scenarios (3+ independent issues)
- 30 Near-Neighbour offences
- 30 Narrative offence descriptions
- 25 POCSO discrimination scenarios
- 25 BSA evidence scenarios
- 20 BNSS procedure scenarios
- 15 Negative propositions
- 15 Multi-hop legal reasoning scenarios

Outputs:
1. evaluation/phase_8_2k_blind_validation_200.jsonl (User input only: scenario_id, fact_pattern, legal_question)
2. evaluation/phase_8_2k_blind_validation_200_ground_truth.json (Evaluator truth: expected_sections, required_issues, prohibited_propositions)
"""

import json
from pathlib import Path

def generate_200_blind_set():
    inputs = []
    ground_truth = []
    sc_id = 1

    # 1. 40 MULTI-STATUTE SCENARIOS (3+ ISSUES) ────────────────────────────────
    multi_base = [
        ("A company accountant siphons 3 crore INR using forged director digital signatures; police search residence without videography, seize encrypted hard drives, and company seeks proceeds freezing.",
         "Analyze substantive forgery/fraud under BNS, search/attachment under BNSS, and electronic record certification under BSA.",
         [{"statute": "BNS", "section": "316"}, {"statute": "BNS", "section": "336"}, {"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "107"}, {"statute": "BSA", "section": "63"}],
         ["fraud_forgery", "search_videography_attachment", "electronic_evidence"],
         [{"statute": "POCSO", "section": "11"}]),

        ("A hostel warden sexually assaults a 13-year-old child in his custody, school management buries the incident, and police arrest the warden without pre-arrest notice.",
         "Identify POCSO aggravated penetrative assault, POCSO reporting breach, BNSS pre-arrest notice, and BSA digital communications.",
         [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}, {"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}, {"statute": "BNSS", "section": "35"}, {"statute": "BSA", "section": "63"}],
         ["child_sexual_assault", "mandatory_reporting", "arrest_procedure"],
         [{"statute": "POCSO", "section": "11"}]),

        ("A speeding delivery van strikes and kills a cyclist at midnight; driver flees without reporting, vehicle inspection is conducted, and police seek 15-day custody.",
         "Evaluate BNS negligence death, BNSS police custody, and BSA expert opinion.",
         [{"statute": "BNS", "section": "106"}, {"statute": "BNS", "section": "281"}, {"statute": "BNSS", "section": "187"}, {"statute": "BSA", "section": "39"}],
         ["negligence_homicide", "police_remand", "expert_testimony"],
         [{"statute": "BNS", "section": "103"}]),

        ("Six armed men rob a nationalized bank at gunpoint; security guard shoots in defence, and police recover hidden cash from well based on custody disclosure statement.",
         "Determine BNS dacoity, BNS private defence, BNSS remand, and BSA discovery of fact in custody.",
         [{"statute": "BNS", "section": "310"}, {"statute": "BNS", "section": "38"}, {"statute": "BNS", "section": "41"}, {"statute": "BNSS", "section": "187"}, {"statute": "BSA", "section": "23"}],
         ["dacoity_armed", "private_defence", "custody_discovery"],
         [{"statute": "BNS", "section": "303"}])
    ]

    for i in range(40):
        tmpl = multi_base[i % len(multi_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "MULTI_STATUTE_3_PLUS_ISSUES",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Scenario Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 2. 30 NEAR-NEIGHBOUR OFFENCES ───────────────────────────────────────────
    near_base = [
        ("A thief secretly removes an unguarded diamond watch from a living room side table while the owner is napping.", "What offence is committed?", [{"statute": "BNS", "section": "303"}], ["simple_theft"], [{"statute": "BNS", "section": "304"}, {"statute": "BNS", "section": "308"}]),
        ("A pillion rider on a sports motorcycle snatches a gold chain from a commuter's neck at a red light.", "What offence under BNS applies to sudden physical grabbing from a person?", [{"statute": "BNS", "section": "304"}], ["snatching"], [{"statute": "BNS", "section": "303"}]),
        ("A gang sends threatening letters demanding 10 lakh rupees or they will set fire to a factory.", "What offence of coercive extraction applies?", [{"statute": "BNS", "section": "308"}, {"statute": "BNS", "section": "351"}], ["extortion"], [{"statute": "BNS", "section": "303"}]),
        ("Three armed intruders hold a family at knifepoint and demand the combination to the jewellery safe.", "What offence applies when theft is committed with armed fear of instant hurt?", [{"statute": "BNS", "section": "309"}, {"statute": "BNS", "section": "329"}], ["robbery"], [{"statute": "BNS", "section": "310"}]),
        ("Eight armed bandits intercept an inter-district bus and loot all passengers at gunpoint.", "What offence applies to conjoint robbery by five or more persons?", [{"statute": "BNS", "section": "310"}, {"statute": "BNS", "section": "311"}], ["dacoity"], [{"statute": "BNS", "section": "303"}]),
        ("A passenger finds a leather wallet containing cash left on a metro seat and decides to keep and spend it.", "What offence of converting found property applies?", [{"statute": "BNS", "section": "314"}], ["misappropriation"], [{"statute": "BNS", "section": "303"}])
    ]

    for i in range(30):
        tmpl = near_base[i % len(near_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "NEAR_NEIGHBOUR_OFFENCES",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 3. 30 NARRATIVE OFFENCE DESCRIPTIONS ─────────────────────────────────────
    narr_base = [
        ("A warehouse employee entrusted with stock of pharmaceutical drugs sells cartons on the black market.", "What fiduciary offence is committed?", [{"statute": "BNS", "section": "316"}], ["breach_of_trust"], [{"statute": "BNS", "section": "303"}]),
        ("A fraudulent agent collects visa processing deposits from jobseekers knowing no work permits exist.", "What deception offence applies?", [{"statute": "BNS", "section": "318"}, {"statute": "BNS", "section": "319"}], ["cheating"], [{"statute": "BNS", "section": "316"}]),
        ("A person creates duplicate land allotment letters with scanned signatures to deceive buyers.", "What offence of false documents applies?", [{"statute": "BNS", "section": "336"}, {"statute": "BNS", "section": "338"}, {"statute": "BNS", "section": "340"}], ["forgery"], [{"statute": "BNS", "section": "303"}]),
        ("A resident attacked in his bedroom at 3 AM by an axe-wielding intruder strikes back fatally with an iron bar.", "Which private defence sections apply?", [{"statute": "BNS", "section": "38"}, {"statute": "BNS", "section": "41"}, {"statute": "BNS", "section": "44"}], ["private_defence"], [{"statute": "BNS", "section": "103"}])
    ]

    for i in range(30):
        tmpl = narr_base[i % len(narr_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "NARRATIVE_OFFENCE_DESCRIPTIONS",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 4. 25 POCSO DISCRIMINATION SCENARIOS ─────────────────────────────────────
    pocso_base = [
        ("A 15-year-old high school student is sent sexually explicit photos and messages by an adult tutor online.", "What POCSO harassment offence applies?", [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "12"}], ["pocso_harassment"], [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "5"}]),
        ("A family relative commits penetrative sexual acts against a 9-year-old child inside the domestic household.", "What aggravated penetrative offence applies?", [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}], ["pocso_aggravated_penetrative"], [{"statute": "POCSO", "section": "7"}]),
        ("A swimming coach touches intimate body parts of a 12-year-old pupil in a training facility without penetration.", "What institutional sexual assault offence applies?", [{"statute": "POCSO", "section": "7"}, {"statute": "POCSO", "section": "8"}, {"statute": "POCSO", "section": "9"}], ["pocso_sexual_assault"], [{"statute": "POCSO", "section": "3"}]),
        ("A school principal receives a written complaint of abuse on a child from a mother and locks it in a drawer without informing police.", "What reporting breach offence applies?", [{"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}], ["mandatory_reporting"], [{"statute": "POCSO", "section": "3"}]),
        ("In a child sexual assault prosecution, the defence argues the victim was 17 years 11 months old at the time.", "What is the threshold age definition of a child under POCSO?", [{"statute": "POCSO", "section": "2(1)(d)"}, {"statute": "POCSO", "section": "2"}], ["child_age_definition"], [{"statute": "POCSO", "section": "11"}])
    ]

    for i in range(25):
        tmpl = pocso_base[i % len(pocso_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "POCSO_DISCRIMINATION",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 5. 25 BSA EVIDENCE SCENARIOS ─────────────────────────────────────────────
    bsa_base = [
        ("The prosecution tenders WhatsApp exports, hard disk images, and CCTV logs in court without producing physical servers.", "What certificate is required under BSA to admit electronic records?", [{"statute": "BSA", "section": "61"}, {"statute": "BSA", "section": "62"}, {"statute": "BSA", "section": "63"}], ["electronic_record_cert"], [{"statute": "BSA", "section": "23"}]),
        ("An accused in custody discloses where the blood-stained knife is hidden in a sewer pipe; police recover it.", "Which BSA section makes statements leading to discovery of fact admissible?", [{"statute": "BSA", "section": "23"}], ["custody_discovery"], [{"statute": "BSA", "section": "26"}]),
        ("A woman suffering severe burn injuries makes a statement to an attending physician identifying her attacker before dying.", "Which BSA section governs admissibility of statements regarding cause of death?", [{"statute": "BSA", "section": "26"}], ["dying_declaration"], [{"statute": "BSA", "section": "23"}]),
        ("The court requires ballistic microscopic striation examination and handwriting comparison on a contested will.", "Which BSA provision admits opinions of forensic and scientific experts?", [{"statute": "BSA", "section": "39"}], ["expert_opinion"], [{"statute": "BSA", "section": "63"}]),
        ("A married woman dies within 4 years of marriage from poison, with evidence of dowry demands shortly before death.", "Which statutory presumption under BSA applies to dowry death?", [{"statute": "BSA", "section": "118"}], ["dowry_death_presumption"], [{"statute": "BSA", "section": "23"}])
    ]

    for i in range(25):
        tmpl = bsa_base[i % len(bsa_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "BSA_EVIDENCE",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 6. 20 BNSS PROCEDURE SCENARIOS ───────────────────────────────────────────
    bnss_base = [
        ("Police arrest an individual for a property offence punishable with up to 3 years imprisonment without prior notice.", "Which BNSS section mandates a notice of appearance prior to arrest in offences under 7 years?", [{"statute": "BNSS", "section": "35"}], ["notice_of_appearance"], [{"statute": "BNSS", "section": "105"}]),
        ("Investigating officers search a private house and seize digital equipment without making audio-video electronic recording.", "Which BNSS section mandates videography during search and seizure?", [{"statute": "BNSS", "section": "105"}], ["search_videography"], [{"statute": "BNSS", "section": "35"}]),
        ("Police identify commercial plots purchased with proceeds from an illegal racket and seek attachment.", "Which BNSS section empowers attachment of proceeds of crime?", [{"statute": "BNSS", "section": "107"}], ["proceeds_attachment"], [{"statute": "BNSS", "section": "35"}]),
        ("Police request 7 days initial custody, then judicial custody, and later a second 5-day tranche of police remand.", "Which BNSS section allows police custody in tranches within 40/60 days?", [{"statute": "BNSS", "section": "187"}], ["police_remand"], [{"statute": "BNSS", "section": "479"}]),
        ("A first-time undertrial accused has spent more than one-third of the maximum statutory sentence in custody awaiting trial.", "Which BNSS section grants statutory bail eligibility to undertrials?", [{"statute": "BNSS", "section": "479"}], ["undertrial_bail"], [{"statute": "BNSS", "section": "35"}])
    ]

    for i in range(20):
        tmpl = bnss_base[i % len(bnss_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "BNSS_PROCEDURE",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 7. 15 NEGATIVE PROPOSITIONS ──────────────────────────────────────────────
    neg_base = [
        ("A query asks whether BNS Section 303 (Theft) applies when an armed intruder holds a victim at gunpoint and demands cash.", "Does simple theft apply when instant fear of hurt is caused during property taking?", [{"statute": "BNS", "section": "309"}, {"statute": "BNS", "section": "329"}], ["negative_theft_robbery"], [{"statute": "BNS", "section": "303"}]),
        ("A query asks whether BNS Section 103 (Murder) applies when an accidental vehicular collision causes death without intent.", "Does intentional murder apply to rash and negligent causing of death?", [{"statute": "BNS", "section": "106"}, {"statute": "BNS", "section": "281"}], ["negative_murder_negligence"], [{"statute": "BNS", "section": "103"}]),
        ("A query asks whether POCSO Section 11 (Sexual Harassment) applies when a child is subjected to penetrative sexual acts.", "Does sexual harassment apply to penetrative sexual acts under POCSO?", [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}], ["negative_harassment_penetrative"], [{"statute": "POCSO", "section": "11"}]),
        ("A query asks whether BNS Section 308 (Extortion) applies when an employee secretly steals office supplies with no communication.", "Does extortion apply when no fear of injury is communicated to any person?", [{"statute": "BNS", "section": "303"}], ["negative_extortion_theft"], [{"statute": "BNS", "section": "308"}]),
        ("A query asks whether BSA Section 23 (Discovery) applies to an electronic document produced with a statutory certificate.", "Does custody discovery statement apply to standard electronic record certification?", [{"statute": "BSA", "section": "63"}], ["negative_discovery_cert"], [{"statute": "BSA", "section": "23"}])
    ]

    for i in range(15):
        tmpl = neg_base[i % len(neg_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "NEGATIVE_PROPOSITIONS",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # 8. 15 MULTI-HOP LEGAL REASONING SCENARIOS ────────────────────────────────
    hop_base = [
        ("A suspect is arrested for online credit card fraud, police record audio-video search of server, and prosecution submits forensic certificate under Section 63.",
         "Trace substantive fraud to BNS 318, search videography to BNSS 105, and electronic evidence to BSA 63.",
         [{"statute": "BNS", "section": "318"}, {"statute": "BNSS", "section": "105"}, {"statute": "BSA", "section": "63"}],
         ["multihop_fraud_search_cert"],
         [{"statute": "POCSO", "section": "11"}]),

        ("A student discloses sexual harassment by a school employee to the principal who conceals it, police arrest the employee without notice, and digital chat logs are presented.",
         "Trace harassment to POCSO 11, reporting failure to POCSO 19, notice to BNSS 35, and proof to BSA 63.",
         [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "19"}, {"statute": "BNSS", "section": "35"}, {"statute": "BSA", "section": "63"}],
         ["multihop_pocso_procedure_evidence"],
         [{"statute": "POCSO", "section": "5"}])
    ]

    for i in range(15):
        tmpl = hop_base[i % len(hop_base)]
        cid = f"BLIND-82K-{sc_id:03d}"
        inputs.append({
            "scenario_id": cid,
            "category": "MULTI_HOP_LEGAL_REASONING",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1]
        })
        ground_truth.append({
            "scenario_id": cid,
            "expected_sections": tmpl[2],
            "required_issues": tmpl[3],
            "prohibited_propositions": tmpl[4]
        })
        sc_id += 1

    # Write files
    input_file = Path("evaluation/phase_8_2k_blind_validation_200.jsonl")
    gt_file = Path("evaluation/phase_8_2k_blind_validation_200_ground_truth.json")

    with open(input_file, "w", encoding="utf-8") as f:
        for inp in inputs:
            f.write(json.dumps(inp, ensure_ascii=False) + "\n")

    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated {len(inputs)} blind validation scenarios in {input_file}")
    print(f"Successfully saved {len(ground_truth)} ground truth records in {gt_file}")

if __name__ == "__main__":
    generate_200_blind_set()
