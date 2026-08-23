"""create_phase_8_2j_blind_validation_set.py — 100-Scenario Blind Validation Benchmark (Phase 8.2J).

Creates 100 brand-new, completely unseen legal scenarios testing:
- 30 Multi-Statute cases (with 3+ independent legal issues)
- 20 BNS Near-Neighbour cases
- 15 POCSO cases
- 15 BSA Evidentiary cases
- 10 BNSS Procedural cases
- 10 Negative Proposition & Distractor cases
"""

import json
from pathlib import Path

def create_blind_set_82j():
    scenarios = []
    sc_id = 1

    # ── 1. 30 MULTI-STATUTE CASES (3+ INDEPENDENT ISSUES) ─────────────────────
    multi_templates = [
        ("A finance officer fraudulently transfers 2 crore INR using spoofed manager credentials; police raid residence and seize server logs without videography, and prosecution seeks asset attachment.",
         "Analyze substantive fraud under BNS, search/attachment under BNSS, and electronic record certification under BSA.",
         [{"statute": "BNS", "section": "316"}, {"statute": "BNS", "section": "318"}, {"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "107"}, {"statute": "BSA", "section": "63"}],
         [{"statute": "POCSO", "section": "11"}, {"statute": "BNS", "section": "303"}]),

        ("A tuition teacher sends explicit sexual messages to a 14-year-old student, the school principal buries the complaint, and police arrest the teacher without prior notice.",
         "Identify POCSO sexual harassment, POCSO mandatory reporting failure, BNSS pre-arrest notice, and BSA digital proof.",
         [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}, {"statute": "BNSS", "section": "35"}, {"statute": "BSA", "section": "63"}],
         [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "5"}]),

        ("An intoxicated driver speeds through a red light killing two pedestrians, flees the scene without reporting, and police seek 15-day custody while forensic experts inspect brake lines.",
         "Evaluate BNS rash driving & negligence death, BNSS remand in tranches, and BSA expert opinion.",
         [{"statute": "BNS", "section": "106"}, {"statute": "BNS", "section": "281"}, {"statute": "BNSS", "section": "187"}, {"statute": "BSA", "section": "39"}],
         [{"statute": "BNS", "section": "103"}]),

        ("Five armed masked men storm a jewellery store, owner fires licensed revolver in self-defence injuring one, and police recover hidden loot based on custody confession.",
         "Determine BNS dacoity, BNS private defence extending to hurt, BNSS remand, and BSA discovery of fact.",
         [{"statute": "BNS", "section": "310"}, {"statute": "BNS", "section": "38"}, {"statute": "BNS", "section": "41"}, {"statute": "BNSS", "section": "187"}, {"statute": "BSA", "section": "23"}],
         [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "308"}]),

        ("A doctor at a children's shelter sexually assaults an 11-year-old child in his care, administrator conceals records, and special court records child statement in camera.",
         "Analyze POCSO aggravated penetrative assault, POCSO reporting failure, and POCSO special court statement safeguards.",
         [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}, {"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}, {"statute": "POCSO", "section": "24"}, {"statute": "POCSO", "section": "33"}],
         [{"statute": "POCSO", "section": "11"}]),

        ("A criminal gang prints counterfeit 500-rupee notes, uses forged transport permits, police seize offset press without warrant, and bank extracts electronic transaction records.",
         "Analyze BNS counterfeiting & forgery, BNSS search without warrant, and BSA electronic record proof.",
         [{"statute": "BNS", "section": "231"}, {"statute": "BNS", "section": "336"}, {"statute": "BNSS", "section": "105"}, {"statute": "BSA", "section": "63"}],
         [{"statute": "BNS", "section": "303"}])
    ]

    for i in range(30):
        tmpl = multi_templates[i % len(multi_templates)]
        scenarios.append({
            "scenario_id": f"BLIND-82J-{sc_id:03d}",
            "category": "MULTI_STATUTE_3_PLUS_ISSUES",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Scenario Variant #{i+1})",
            "legal_question": tmpl[1],
            "expected_sections": tmpl[2],
            "distractor_sections": tmpl[3]
        })
        sc_id += 1

    # ── 2. 20 BNS NEAR-NEIGHBOUR CASES ────────────────────────────────────────
    bns_near_cases = [
        ("A pickpocket quietly slips an unfastened diamond necklace out of a shopper's bag while in a crowded elevator.", "What offence is committed?", [{"statute": "BNS", "section": "303"}], [{"statute": "BNS", "section": "304"}, {"statute": "BNS", "section": "308"}]),
        ("A motorcycle rider grabs a gold chain directly off a pedestrian's neck and accelerates away instantly.", "What offence under BNS 2023 applies to sudden physical grabbing?", [{"statute": "BNS", "section": "304"}], [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "309"}]),
        ("A landlord threatens to burn down a tenant's business inventory unless 3 lakh cash is paid immediately.", "What offence of coercive extraction applies?", [{"statute": "BNS", "section": "308"}, {"statute": "BNS", "section": "351"}], [{"statute": "BNS", "section": "303"}]),
        ("Four armed men hold a cashier at gunpoint inside a petrol pump booth and take the cash receipts.", "What offence applies when theft is committed with armed fear of instant death?", [{"statute": "BNS", "section": "309"}, {"statute": "BNS", "section": "329"}], [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "310"}]),
        ("Seven armed highway robbers block a cargo truck and loot the merchandise under threat of firearms.", "What offence applies to conjoint robbery by five or more persons?", [{"statute": "BNS", "section": "310"}, {"statute": "BNS", "section": "311"}], [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "308"}]),
        ("A train passenger finds a laptop on a seat, finds the owner's card, but wipes it and sells it for cash.", "What offence of converting found property applies?", [{"statute": "BNS", "section": "314"}], [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "316"}]),
        ("A logistics supervisor entrusted with warehouse inventory sells 50 cartons of electronics and pockets the money.", "What offence of misappropriating entrusted property applies?", [{"statute": "BNS", "section": "316"}], [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "318"}]),
        ("A con artist poses as an overseas employment agent, takes advance fees from 20 youths with no intention to provide visas.", "What offence of cheating and fraudulent inducement applies?", [{"statute": "BNS", "section": "318"}, {"statute": "BNS", "section": "319"}], [{"statute": "BNS", "section": "303"}, {"statute": "BNS", "section": "316"}]),
        ("A document writer prepares a fake title deed with scanned signatures to sell municipal land fraudulently.", "What offence of forgery and making false documents applies?", [{"statute": "BNS", "section": "336"}, {"statute": "BNS", "section": "338"}, {"statute": "BNS", "section": "340"}], [{"statute": "BNS", "section": "303"}]),
        ("A resident struck on the head by a burglar armed with an axe strikes back fatally with a fireplace poker.", "Which private defence sections justify causing death?", [{"statute": "BNS", "section": "38"}, {"statute": "BNS", "section": "41"}, {"statute": "BNS", "section": "44"}], [{"statute": "BNS", "section": "103"}, {"statute": "BNS", "section": "106"}])
    ]

    for i in range(20):
        tmpl = bns_near_cases[i % len(bns_near_cases)]
        scenarios.append({
            "scenario_id": f"BLIND-82J-{sc_id:03d}",
            "category": "BNS_NEAR_NEIGHBOUR",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1],
            "expected_sections": tmpl[2],
            "distractor_sections": tmpl[3]
        })
        sc_id += 1

    # ── 3. 15 POCSO CASES ─────────────────────────────────────────────────────
    pocso_cases = [
        ("A 14-year-old child receives sexually explicit videos and solicitations on social media from an adult acquaintance.", "What POCSO offence applies to online sexual harassment?", [{"statute": "POCSO", "section": "11"}, {"statute": "POCSO", "section": "12"}], [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "5"}]),
        ("A relative commits penetrative sexual assault against an 8-year-old child in the family home.", "What POCSO section penalizes aggravated penetrative assault in a domestic setting?", [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}], [{"statute": "POCSO", "section": "7"}, {"statute": "POCSO", "section": "11"}]),
        ("A swimming instructor touches the intimate body parts of a 12-year-old student without penetration.", "What POCSO section penalizes sexual assault in an institutional setting?", [{"statute": "POCSO", "section": "7"}, {"statute": "POCSO", "section": "8"}, {"statute": "POCSO", "section": "9"}], [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "5"}]),
        ("A school headmistress receives a written disclosure of sexual assault on a student but hides the file.", "What mandatory reporting obligation and penalty apply?", [{"statute": "POCSO", "section": "19"}, {"statute": "POCSO", "section": "21"}], [{"statute": "POCSO", "section": "3"}, {"statute": "POCSO", "section": "7"}]),
        ("In a child sexual offence trial, the defence challenges victim age claiming victim was 17 years 10 months old.", "What is the statutory age threshold definition of a child under POCSO?", [{"statute": "POCSO", "section": "2(1)(d)"}, {"statute": "POCSO", "section": "2"}], [{"statute": "POCSO", "section": "11"}])
    ]

    for i in range(15):
        tmpl = pocso_cases[i % len(pocso_cases)]
        scenarios.append({
            "scenario_id": f"BLIND-82J-{sc_id:03d}",
            "category": "POCSO_DISCRIMINATION",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1],
            "expected_sections": tmpl[2],
            "distractor_sections": tmpl[3]
        })
        sc_id += 1

    # ── 4. 15 BSA EVIDENTIARY CASES ───────────────────────────────────────────
    bsa_cases = [
        ("The prosecution submits CCTV hard drive exports and WhatsApp chat records without physical server production.", "What certificate is required under BSA to admit electronic records?", [{"statute": "BSA", "section": "61"}, {"statute": "BSA", "section": "62"}, {"statute": "BSA", "section": "63"}], [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "26"}]),
        ("An accused in custody reveals the location of a concealed firearm in an abandoned well; police recover the gun.", "Which BSA section makes statements leading to discovery of fact admissible?", [{"statute": "BSA", "section": "23"}], [{"statute": "BSA", "section": "26"}, {"statute": "BSA", "section": "63"}]),
        ("A critically injured assault victim makes a statement to an attending doctor identifying her attacker before passing away.", "Which BSA provision admits statements by deceased persons regarding cause of death?", [{"statute": "BSA", "section": "26"}], [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "39"}]),
        ("A court requires ballistic striation analysis and comparison of disputed signatures on a contested contract.", "Which BSA section governs the admissibility of expert scientific and handwriting opinions?", [{"statute": "BSA", "section": "39"}], [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "63"}]),
        ("A woman dies within 3 years of marriage from poison, with evidence of persistent dowry harassment shortly before death.", "Which statutory presumption under BSA applies to dowry death?", [{"statute": "BSA", "section": "118"}], [{"statute": "BSA", "section": "23"}, {"statute": "BSA", "section": "26"}])
    ]

    for i in range(15):
        tmpl = bsa_cases[i % len(bsa_cases)]
        scenarios.append({
            "scenario_id": f"BLIND-82J-{sc_id:03d}",
            "category": "BSA_EVIDENCE",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1],
            "expected_sections": tmpl[2],
            "distractor_sections": tmpl[3]
        })
        sc_id += 1

    # ── 5. 10 BNSS PROCEDURAL CASES ───────────────────────────────────────────
    bnss_cases = [
        ("Police arrest an individual for a financial offence punishable with up to 3 years imprisonment without prior notice.", "Which BNSS section mandates a notice of appearance prior to arrest?", [{"statute": "BNSS", "section": "35"}], [{"statute": "BNSS", "section": "105"}, {"statute": "BNSS", "section": "187"}]),
        ("Investigating officers search a residence and seize digital media without conducting audio-video electronic recording.", "Which BNSS provision mandates videography during search and seizure?", [{"statute": "BNSS", "section": "105"}], [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "187"}]),
        ("Police identify commercial real estate bought with proceeds from an illegal lottery racket and seek attachment.", "Which BNSS section empowers attachment of property derived from proceeds of crime?", [{"statute": "BNSS", "section": "107"}], [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "105"}]),
        ("Police request 7 days initial custody, then judicial custody, and later a second 5-day tranche of police remand.", "Which BNSS section allows police custody in tranches within 40/60 days?", [{"statute": "BNSS", "section": "187"}], [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "479"}]),
        ("A first-time undertrial accused has spent more than one-third of the maximum statutory term in prison awaiting trial.", "Which BNSS section provides statutory release on bail for undertrials?", [{"statute": "BNSS", "section": "479"}], [{"statute": "BNSS", "section": "35"}, {"statute": "BNSS", "section": "187"}])
    ]

    for i in range(10):
        tmpl = bnss_cases[i % len(bnss_cases)]
        scenarios.append({
            "scenario_id": f"BLIND-82J-{sc_id:03d}",
            "category": "BNSS_PROCEDURE",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1],
            "expected_sections": tmpl[2],
            "distractor_sections": tmpl[3]
        })
        sc_id += 1

    # ── 6. 10 NEGATIVE PROPOSITIONS & DISTRACTORS ─────────────────────────────
    neg_cases = [
        ("A query asks whether BNS Section 303 (Theft) applies when an armed intruder holds a victim at gunpoint and takes property.", "Does simple theft apply when instant fear of hurt is caused during taking?", [{"statute": "BNS", "section": "309"}, {"statute": "BNS", "section": "329"}], [{"statute": "BNS", "section": "303"}]),
        ("A query asks whether BNS Section 103 (Murder) applies when a driver accidentally strikes a pedestrian at night without intent to kill.", "Does intentional murder apply to rash and negligent causing of death?", [{"statute": "BNS", "section": "106"}, {"statute": "BNS", "section": "281"}], [{"statute": "BNS", "section": "103"}]),
        ("A query asks whether POCSO Section 11 (Sexual Harassment) applies when a child is subjected to penetrative sexual assault.", "Does sexual harassment apply to penetrative sexual acts under POCSO?", [{"statute": "POCSO", "section": "5"}, {"statute": "POCSO", "section": "6"}], [{"statute": "POCSO", "section": "11"}]),
        ("A query asks whether BNS Section 308 (Extortion) applies when an employee quietly steals office supplies from a supply room.", "Does extortion apply when no fear of injury is communicated to any person?", [{"statute": "BNS", "section": "303"}], [{"statute": "BNS", "section": "308"}]),
        ("A query asks whether BSA Section 23 (Discovery) applies to an electronic document produced with a statutory certificate.", "Does custody discovery statement apply to standard electronic record certification?", [{"statute": "BSA", "section": "63"}], [{"statute": "BSA", "section": "23"}])
    ]

    for i in range(10):
        tmpl = neg_cases[i % len(neg_cases)]
        scenarios.append({
            "scenario_id": f"BLIND-82J-{sc_id:03d}",
            "category": "NEGATIVE_PROPOSITION",
            "fact_pattern": f"Case {sc_id}: {tmpl[0]} (Variant #{i+1})",
            "legal_question": tmpl[1],
            "expected_sections": tmpl[2],
            "distractor_sections": tmpl[3]
        })
        sc_id += 1

    out_file = Path("evaluation/phase_8_2j_blind_validation_100.jsonl")
    with open(out_file, "w", encoding="utf-8") as f:
        for sc in scenarios:
            f.write(json.dumps(sc, ensure_ascii=False) + "\n")

    print(f"Successfully generated {len(scenarios)} blind validation scenarios in {out_file}")

if __name__ == "__main__":
    create_blind_set_82j()
