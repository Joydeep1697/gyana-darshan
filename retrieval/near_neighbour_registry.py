"""near_neighbour_registry.py — Nyaya Legal OS Near-Neighbour Legal Families Registry (Phase 8.2K).

Defines legally adjacent section clusters and their distinguishing factual elements:
1. Property Offences (Theft, Snatching, Extortion, Robbery, Dacoity, Misappropriation, CBT, Cheating)
2. Bodily Offences (Murder, Culpable Homicide, Negligence, Hurt, Grievous Hurt, Private Defence)
3. Sexual Offences against Children (POCSO Penetrative, Assault, Harassment, Reporting, Procedure)
4. Procedural Safeguards (BNSS Notice, Search Videography, Attachment, Remand, Bail)
5. Evidentiary Rules (BSA Electronic Certs, Discovery, Dying Declaration, Expert Testimony, Presumptions)
"""

from typing import Dict, List, Any, Set, Tuple

NEAR_NEIGHBOUR_FAMILIES = {
    # ── 1. PROPERTY OFFENCE CLUSTERS (BNS) ───────────────────────────────────
    "theft_vs_snatching_vs_extortion_vs_robbery_vs_dacoity": {
        "statute": "BNS",
        "members": {
            "303": {
                "concept": "theft",
                "distinguishing_elements": ["dishonest_taking", "movable_property", "out_of_possession", "without_consent", "secret_taking"],
                "negating_elements": ["sudden_grab_body", "fear_instant_hurt", "fear_instant_death", "armed_coercion", "gang_of_five", "extortionate_threat"]
            },
            "304": {
                "concept": "snatching",
                "distinguishing_elements": ["sudden_grab_body", "moving_vehicle_grab", "snatching_chain_purse", "quick_escape"],
                "negating_elements": ["secret_taking", "pre_existing_entrustment", "gang_of_five"]
            },
            "308": {
                "concept": "extortion",
                "distinguishing_elements": ["extortionate_threat", "fear_of_injury", "dishonest_inducement_to_deliver", "future_threat", "demand_letter", "blackmail"],
                "negating_elements": ["secret_taking", "instant_armed_force_present"]
            },
            "309": {
                "concept": "robbery",
                "distinguishing_elements": ["theft_or_extortion_with_instant_fear", "armed_fear_instant_hurt", "gunpoint_knifepoint", "forced_safe_open"],
                "negating_elements": ["gang_of_five_or_more", "secret_taking_without_fear"]
            },
            "310": {
                "concept": "dacoity",
                "distinguishing_elements": ["gang_of_five_or_more", "conjoint_robbery", "highway_armed_gang"],
                "negating_elements": ["single_offender", "less_than_five_persons"]
            },
            "314": {
                "concept": "dishonest_misappropriation",
                "distinguishing_elements": ["found_lost_property", "converted_to_own_use", "property_left_behind_train_seat", "not_taken_from_possession"],
                "negating_elements": ["taken_directly_from_person", "fiduciary_entrustment"]
            },
            "316": {
                "concept": "criminal_breach_of_trust",
                "distinguishing_elements": ["fiduciary_entrustment", "warehouse_manager_custody", "accountant_cashier_dominion", "dishonest_conversion_of_entrusted_goods"],
                "negating_elements": ["taking_from_stranger", "found_lost_item"]
            },
            "318": {
                "concept": "cheating",
                "distinguishing_elements": ["fraudulent_inducement", "deceit_from_inception", "fake_scheme_visa", "persuading_delivery_by_false_promise"],
                "negating_elements": ["lawful_entrustment_subsequently_breached", "physical_force"]
            }
        }
    },

    # ── 2. HOMICIDE & PRIVATE DEFENCE CLUSTERS (BNS) ─────────────────────────
    "homicide_vs_negligence_vs_private_defence": {
        "statute": "BNS",
        "members": {
            "38": {
                "concept": "private_defence_general",
                "distinguishing_elements": ["repelling_unlawful_aggression", "reasonable_apprehension_danger", "proportional_defence"],
                "negating_elements": ["premeditated_attack", "aggressor_fleeing"]
            },
            "41": {
                "concept": "private_defence_causing_death",
                "distinguishing_elements": ["apprehension_of_death_or_grievous_hurt", "armed_burglar_housebreaking_at_night", "rape_apprehension"],
                "negating_elements": ["minor_theft_without_threat", "excessive_force_after_threat_ceased"]
            },
            "103": {
                "concept": "murder",
                "distinguishing_elements": ["intention_to_cause_death", "bodily_injury_sufficient_in_ordinary_course", "lynching_intentional_killing"],
                "negating_elements": ["rash_negligent_driving", "justified_private_defence", "sudden_fight_without_premeditation"]
            },
            "106": {
                "concept": "death_by_negligence",
                "distinguishing_elements": ["rash_or_negligent_act", "hit_and_run_pedestrian", "vehicular_collision", "intoxicated_driving", "structural_collapse_negligence"],
                "negating_elements": ["deliberate_intention_to_kill", "premeditated_murder"]
            }
        }
    },

    # ── 3. POCSO SPECIAL ACT CLUSTERS ────────────────────────────────────────
    "pocso_special_offence_clusters": {
        "statute": "POCSO",
        "members": {
            "5": {
                "concept": "aggravated_penetrative_sexual_assault",
                "distinguishing_elements": ["penetrative_act", "relative_domestic_household", "police_officer_custody", "doctor_teacher_management", "child_below_12"],
                "negating_elements": ["non_penetrative_touching", "online_messages_only"]
            },
            "7": {
                "concept": "sexual_assault_non_penetrative",
                "distinguishing_elements": ["non_penetrative_touching", "touching_intimate_parts", "physical_sexual_contact_without_penetration"],
                "negating_elements": ["penetrative_sexual_act", "online_messages_without_touching"]
            },
            "11": {
                "concept": "sexual_harassment_child",
                "distinguishing_elements": ["explicit_sexual_messages", "online_coercion", "soliciting_explicit_photos", "verbal_gestural_harassment"],
                "negating_elements": ["physical_penetrative_act", "physical_touching_assault"]
            },
            "19": {
                "concept": "mandatory_reporting_duty",
                "distinguishing_elements": ["duty_to_report_to_police_cwc", "headmaster_principal_institution_head", "parent_disclosure_concealed"],
                "negating_elements": ["immediate_reporting_complaint_forwarded"]
            },
            "21": {
                "concept": "penalty_for_failure_to_report",
                "distinguishing_elements": ["failure_to_report_punishment", "six_months_or_one_year_jail", "in_charge_concealing"],
                "negating_elements": ["prompt_fir_registration"]
            },
            "24": {
                "concept": "recording_child_statement_police",
                "distinguishing_elements": ["statement_recorded_at_residence", "police_not_in_uniform", "no_night_detention_of_child"],
                "negating_elements": ["adult_trial_procedure"]
            },
            "33": {
                "concept": "special_court_procedure",
                "distinguishing_elements": ["child_friendly_atmosphere", "frequent_breaks", "no_aggressive_cross_examination", "in_camera_trial"],
                "negating_elements": ["ordinary_sessions_trial"]
            }
        }
    },

    # ── 4. BNSS PROCEDURAL CLUSTERS ──────────────────────────────────────────
    "bnss_procedural_clusters": {
        "statute": "BNSS",
        "members": {
            "35": {
                "concept": "notice_of_appearance_pre_arrest",
                "distinguishing_elements": ["offence_punishable_under_7_years", "notice_of_appearance_mandate", "arrest_without_notice_illegal"],
                "negating_elements": ["heinous_offence_over_7_years", "habitual_offender_warrant"]
            },
            "105": {
                "concept": "search_and_seizure_videography",
                "distinguishing_elements": ["audio_video_electronic_recording_mandate", "search_memo_videography", "warrantless_premises_search"],
                "negating_elements": ["standard_court_summons"]
            },
            "107": {
                "concept": "attachment_of_proceeds_of_crime",
                "distinguishing_elements": ["attachment_powers", "proceeds_of_crime", "freezing_bank_accounts_properties_derived_from_offence"],
                "negating_elements": ["regular_evidence_production"]
            },
            "187": {
                "concept": "police_custody_and_remand",
                "distinguishing_elements": ["15_day_police_custody_in_tranches", "initial_40_or_60_days_remand", "magistrate_authorizing_detention"],
                "negating_elements": ["post_trial_conviction_sentence"]
            },
            "479": {
                "concept": "undertrial_statutory_bail",
                "distinguishing_elements": ["one_third_detention_first_time_offender", "one_half_detention_general_undertrial", "mandatory_release_on_bail"],
                "negating_elements": ["offence_punishable_with_death_life"]
            }
        }
    },

    # ── 5. BSA EVIDENTIARY CLUSTERS ──────────────────────────────────────────
    "bsa_evidentiary_clusters": {
        "statute": "BSA",
        "members": {
            "23": {
                "concept": "discovery_of_fact_in_custody",
                "distinguishing_elements": ["information_received_from_accused_in_custody", "distinct_fact_discovered_thereby", "recovery_of_weapon_property"],
                "negating_elements": ["voluntary_pre_custody_testimony", "electronic_record_certification"]
            },
            "26": {
                "concept": "dying_declaration",
                "distinguishing_elements": ["statement_as_to_cause_of_death", "person_since_deceased", "burn_victim_hospital_statement"],
                "negating_elements": ["victim_surviving_trial", "routine_witness_statement"]
            },
            "39": {
                "concept": "expert_opinion",
                "distinguishing_elements": ["scientific_opinion", "ballistics_handwriting_expert", "medical_board_report", "chemical_forensic_examiner"],
                "negating_elements": ["eye_witness_testimony"]
            },
            "63": {
                "concept": "electronic_record_certificate",
                "distinguishing_elements": ["certificate_under_section_63", "cctv_server_logs_whatsapp_export", "hash_value_device_admissibility", "secondary_electronic_proof"],
                "negating_elements": ["primary_original_physical_document"]
            },
            "118": {
                "concept": "presumption_dowry_death",
                "distinguishing_elements": ["death_within_7_years_of_marriage", "unnatural_burns_poison", "cruelty_for_dowry_shortly_before_death", "statutory_presumption"],
                "negating_elements": ["male_victim", "natural_disease_death"]
            }
        }
    }
}

class NearNeighbourRegistry:
    def __init__(self):
        self.families = NEAR_NEIGHBOUR_FAMILIES

    def find_matching_family(self, matched_sections: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        matched_families = []
        for fam_name, fam_data in self.families.items():
            st = fam_data["statute"]
            members = fam_data["members"]
            # Check if any section in matched_sections is in this family
            hit_members = []
            for st_in, sec_in in matched_sections:
                if st_in.upper() == st.upper() and sec_in in members:
                    hit_members.append(sec_in)
            if hit_members:
                matched_families.append({
                    "family_name": fam_name,
                    "statute": st,
                    "hit_members": hit_members,
                    "all_members": list(members.keys()),
                    "members_meta": members
                })
        return matched_families

    def discriminate_family(
        self,
        family_name: str,
        query_elements: Set[str],
        negated_elements: Set[str]
    ) -> List[Tuple[str, float]]:
        fam_data = self.families.get(family_name)
        if not fam_data:
            return []

        scores = []
        members = fam_data["members"]
        for sec, meta in members.items():
            score = 0.0
            dist_elems = meta.get("distinguishing_elements", [])
            neg_elems = meta.get("negating_elements", [])

            # Positive matches
            for elem in dist_elems:
                if elem in query_elements:
                    score += 25.0

            # Negative penalties
            for neg in neg_elems:
                if neg in query_elements or neg in negated_elements:
                    score -= 50.0

            scores.append((sec, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
