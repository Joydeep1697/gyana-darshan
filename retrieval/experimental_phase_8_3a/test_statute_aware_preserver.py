# test_statute_aware_preserver.py — Unit Test Suite for Phase 8.3A Candidate Preservation
#
# Tests:
# 1. Single-statute query
# 2. Two-statute query
# 3. Three-statute query
# 4. Strong secondary statute survival
# 5. Weak secondary statute suppression (no artificial promotion)
# 6. Irrelevant statute branch filtering
# 7. Duplicate candidate handling
# 8. Preservation threshold boundary condition
# 9. No eligible preservation candidate handling
# 10. Global dominant-statute scenario
# 11. Deterministic repeated execution

import unittest
import sys
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.experimental_phase_8_3a.statute_aware_preserver import StatuteAwarePreserver, StatuteCandidate
from retrieval.experimental_phase_8_3a.phase_8_3a_config import (
    get_config_a, get_config_b, get_config_c, get_config_d, Phase83AConfig
)

class TestStatuteAwarePreserver(unittest.TestCase):

    def setUp(self):
        self.preserver = StatuteAwarePreserver(config=get_config_c())

    def test_01_single_statute_query(self):
        """Test single-statute query behaves correctly without injecting spurious statutes."""
        query = "What is the punishment for theft of movable property under BNS?"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "303", "heading": "Theft", "text": "Whoever intending to take dishonestly...", "branch_score": 60.0, "is_deterministic": False},
                {"statute": "BNS", "section": "304", "heading": "Snatching", "text": "Theft is snatching if...", "branch_score": 40.0, "is_deterministic": False},
                {"statute": "BNS", "section": "305", "heading": "Theft in dwelling house", "text": "Theft in building...", "branch_score": 35.0, "is_deterministic": False},
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["theft"], "weight": 2.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["statute"], "BNS")
        self.assertEqual(results[0]["section"], "303")
        # All returned sections should be BNS
        statutes = set(r["statute"] for r in results)
        self.assertEqual(statutes, {"BNS"})

    def test_02_two_statute_query(self):
        """Test two-statute query preserves both substantive and procedural branches."""
        query = "Theft of laptop and 15 days police custody remand under BNSS"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "303", "heading": "Theft", "text": "Dishonest taking of movable property", "branch_score": 65.0, "is_deterministic": False},
                {"statute": "BNS", "section": "304", "heading": "Snatching", "text": "Snatching definition", "branch_score": 45.0, "is_deterministic": False},
                {"statute": "BNS", "section": "305", "heading": "Theft in building", "text": "Theft inside structure", "branch_score": 30.0, "is_deterministic": False},
                {"statute": "BNS", "section": "308", "heading": "Extortion", "text": "Extortion definition", "branch_score": 25.0, "is_deterministic": False},
            ],
            "BNSS": [
                {"statute": "BNSS", "section": "187", "heading": "Procedure when investigation cannot be completed in twenty-four hours (remand and police custody)", "text": "Magistrate authorization of custody for fifteen days...", "branch_score": 70.0, "is_deterministic": False},
                {"statute": "BNSS", "section": "35", "heading": "Notice of appearance", "text": "Police officer notice...", "branch_score": 20.0, "is_deterministic": False},
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["theft"], "weight": 2.0},
            {"issue_type": "REMAND", "statute_candidates": ["BNSS"], "matched_concepts": ["police custody", "remand"], "weight": 2.5}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        top5_statutes = set(r["statute"] for r in results[:5])
        self.assertIn("BNS", top5_statutes)
        self.assertIn("BNSS", top5_statutes)
        
        # Verify BNSS 187 is in top 3
        bnss_ranks = [r["rank"] for r in results if r["statute"] == "BNSS" and r["section"] == "187"]
        self.assertTrue(len(bnss_ranks) > 0)
        self.assertLessEqual(bnss_ranks[0], 3)

    def test_03_three_statute_query(self):
        """Test multi-statute query across BNS, BNSS, and BSA preserves all three branches."""
        query = "Public contract forgery using electronic records, police custody remand, and electronic admissibility certificate"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "336", "heading": "Forgery", "text": "Making false document", "branch_score": 60.0, "is_deterministic": False},
                {"statute": "BNS", "section": "340", "heading": "Forged document or electronic record", "text": "Using as genuine a forged electronic record", "branch_score": 55.0, "is_deterministic": False},
                {"statute": "BNS", "section": "318", "heading": "Cheating", "text": "Cheating and dishonestly inducing", "branch_score": 40.0, "is_deterministic": False},
                {"statute": "BNS", "section": "316", "heading": "Criminal breach of trust", "text": "Entrusted with property", "branch_score": 35.0, "is_deterministic": False}
            ],
            "BNSS": [
                {"statute": "BNSS", "section": "187", "heading": "Procedure when investigation cannot be completed (remand/custody)", "text": "Police custody authorized", "branch_score": 60.0, "is_deterministic": False},
                {"statute": "BNSS", "section": "35", "heading": "Notice of appearance", "text": "Notice before arrest", "branch_score": 35.0, "is_deterministic": False}
            ],
            "BSA": [
                {"statute": "BSA", "section": "63", "heading": "Admissibility of electronic records", "text": "Certificate for electronic evidence", "branch_score": 65.0, "is_deterministic": False},
                {"statute": "BSA", "section": "61", "heading": "Electronic records as documentary evidence", "text": "Primary and secondary electronic evidence", "branch_score": 40.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["forgery"], "weight": 2.0},
            {"issue_type": "REMAND", "statute_candidates": ["BNSS"], "matched_concepts": ["police custody"], "weight": 2.0},
            {"issue_type": "ELECTRONIC_EVIDENCE", "statute_candidates": ["BSA"], "matched_concepts": ["electronic records", "admissibility"], "weight": 2.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=6)
        top5_statutes = set(r["statute"] for r in results[:5])
        self.assertIn("BNS", top5_statutes)
        self.assertIn("BNSS", top5_statutes)
        self.assertIn("BSA", top5_statutes)

    def test_04_strong_secondary_statute_survival(self):
        """Test strong secondary statute candidate survives dominant statute competition."""
        query = "Cheating contract dispute with electronic WhatsApp evidence certificate"
        # BNS has 5 candidates with high branch scores
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "318", "heading": "Cheating", "text": "Cheating...", "branch_score": 80.0, "is_deterministic": False},
                {"statute": "BNS", "section": "319", "heading": "Cheating by personation", "text": "Personation...", "branch_score": 75.0, "is_deterministic": False},
                {"statute": "BNS", "section": "316", "heading": "Criminal breach of trust", "text": "Trust...", "branch_score": 70.0, "is_deterministic": False},
                {"statute": "BNS", "section": "336", "heading": "Forgery", "text": "False document...", "branch_score": 68.0, "is_deterministic": False},
                {"statute": "BNS", "section": "340", "heading": "Forged record", "text": "Forged...", "branch_score": 65.0, "is_deterministic": False},
            ],
            "BSA": [
                {"statute": "BSA", "section": "63", "heading": "Admissibility of electronic records (WhatsApp and digital logs)", "text": "Certificate required for electronic records...", "branch_score": 62.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["cheating"], "weight": 2.0},
            {"issue_type": "ELECTRONIC_EVIDENCE", "statute_candidates": ["BSA"], "matched_concepts": ["electronic records"], "weight": 2.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        # Without preservation, 5 BNS candidates would occupy ranks 1-5.
        # With preservation, BSA 63 MUST be within ranks 1-5.
        bsa_ranks = [r["rank"] for r in results if r["statute"] == "BSA" and r["section"] == "63"]
        self.assertTrue(len(bsa_ranks) > 0)
        self.assertLessEqual(bsa_ranks[0], 5)

    def test_05_weak_secondary_statute_suppressed(self):
        """Test weak/spurious secondary candidate is NOT artificially promoted."""
        query = "Armed robbery with deadly weapon"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "309", "heading": "Robbery", "text": "Robbery definition", "branch_score": 85.0, "is_deterministic": False},
                {"statute": "BNS", "section": "310", "heading": "Dacoity", "text": "Dacoity definition", "branch_score": 75.0, "is_deterministic": False},
                {"statute": "BNS", "section": "311", "heading": "Robbery with attempt to cause death", "text": "Deadly weapon robbery", "branch_score": 70.0, "is_deterministic": False}
            ],
            "BSA": [
                # Spurious / weak match with very low branch score and no issue alignment
                {"statute": "BSA", "section": "1", "heading": "Short title and commencement", "text": "This Act may be called...", "branch_score": 2.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["robbery"], "weight": 3.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=3)
        # BSA Section 1 should NOT be protected or present in top results
        statutes = [r["statute"] for r in results]
        self.assertNotIn("BSA", statutes[:3])

    def test_06_irrelevant_statute_branch_filtered(self):
        """Test completely irrelevant statute branch is omitted."""
        query = "Murder and culpable homicide"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "101", "heading": "Murder", "text": "Culpable homicide is murder...", "branch_score": 90.0, "is_deterministic": False}
            ],
            "POCSO": [
                {"statute": "POCSO", "section": "2", "heading": "Definitions", "text": "In this Act unless the context...", "branch_score": 0.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["murder"], "weight": 2.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["statute"], "BNS")

    def test_07_duplicate_candidate_handling(self):
        """Test duplicate candidates are cleanly deduplicated."""
        query = "Extortion under BNS"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "308", "heading": "Extortion", "text": "Whoever intentionally puts...", "branch_score": 80.0, "is_deterministic": False},
                {"statute": "BNS", "section": "308", "heading": "Extortion (duplicate copy)", "text": "Whoever intentionally puts...", "branch_score": 75.0, "is_deterministic": False},
                {"statute": "BNS", "section": "308(2)", "heading": "Extortion punishment", "text": "Punishment for extortion", "branch_score": 70.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["extortion"], "weight": 2.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        sections = [r["section"] for r in results]
        self.assertEqual(len(sections), len(set(sections)))

    def test_08_threshold_boundary_condition(self):
        """Test candidate just below vs just above threshold."""
        query = "Bail application under BNSS"
        issues = [{"issue_type": "BAIL", "statute_candidates": ["BNSS"], "weight": 2.0}]

        # Candidate below threshold
        cand_below = {"statute": "BNSS", "section": "1", "heading": "Title", "text": "Short title", "branch_score": 5.0, "is_deterministic": False}
        res_below = self.preserver.preserve_and_fuse(query, {"BNSS": [cand_below]}, issues, top_k=3)
        self.assertFalse(res_below[0].get("is_protected", False))

        # Candidate above threshold
        cand_above = {"statute": "BNSS", "section": "480", "heading": "Bail in non-bailable offences", "text": "When any person accused of bail...", "branch_score": 60.0, "is_deterministic": False}
        res_above = self.preserver.preserve_and_fuse(query, {"BNSS": [cand_above]}, issues, top_k=3)
        self.assertTrue(res_above[0].get("is_protected", False))

    def test_09_no_eligible_preservation_candidate(self):
        """Test graceful fallback when no candidate meets preservation threshold."""
        query = "Random query with vague terminology"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "1", "heading": "Short title", "text": "Act called...", "branch_score": 2.0, "is_deterministic": False}
            ]
        }
        issues = []
        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rank"], 1)

    def test_10_dominant_statute_scenario(self):
        """Test heavily unbalanced candidate pool preserves secondary active branch."""
        query = "Hit and run vehicle accident with search videography procedure under BNSS"
        # BNS has 6 strong entries
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "106", "heading": "Causing death by negligence", "text": "Hit and run vehicle accident", "branch_score": 90.0, "is_deterministic": False},
                {"statute": "BNS", "section": "281", "heading": "Rash driving on public way", "text": "Rash driving...", "branch_score": 85.0, "is_deterministic": False},
                {"statute": "BNS", "section": "125", "heading": "Act endangering life", "text": "Endangering...", "branch_score": 75.0, "is_deterministic": False},
                {"statute": "BNS", "section": "115", "heading": "Voluntarily causing hurt", "text": "Hurt...", "branch_score": 70.0, "is_deterministic": False},
                {"statute": "BNS", "section": "324", "heading": "Mischief", "text": "Mischief...", "branch_score": 65.0, "is_deterministic": False},
            ],
            "BNSS": [
                {"statute": "BNSS", "section": "105", "heading": "Audio video electronic recording of search and seizure", "text": "Search and seizure videography mandatory...", "branch_score": 75.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["hit and run", "rash driving"], "weight": 2.0},
            {"issue_type": "CRIMINAL_PROCEDURE", "statute_candidates": ["BNSS"], "matched_concepts": ["search and seizure", "videography"], "weight": 2.0}
        ]

        results = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        statutes_in_top5 = [r["statute"] for r in results[:5]]
        self.assertIn("BNSS", statutes_in_top5)
        # BNSS 105 must be within Top-3
        bnss_rank = [r["rank"] for r in results if r["statute"] == "BNSS" and r["section"] == "105"][0]
        self.assertLessEqual(bnss_rank, 3)

    def test_11_deterministic_repeated_execution(self):
        """Test multiple executions produce exact identical output rankings."""
        query = "Stalking, voyeurism and electronic chat admissibility under BSA"
        branch_results = {
            "BNS": [
                {"statute": "BNS", "section": "77", "heading": "Voyeurism", "text": "Capturing images...", "branch_score": 65.0, "is_deterministic": False},
                {"statute": "BNS", "section": "78", "heading": "Stalking", "text": "Following woman...", "branch_score": 65.0, "is_deterministic": False}
            ],
            "BSA": [
                {"statute": "BSA", "section": "63", "heading": "Admissibility of electronic records", "text": "Certificate required...", "branch_score": 65.0, "is_deterministic": False}
            ]
        }
        issues = [
            {"issue_type": "SUBSTANTIVE_OFFENCE", "statute_candidates": ["BNS"], "matched_concepts": ["stalking", "voyeurism"], "weight": 2.0},
            {"issue_type": "ELECTRONIC_EVIDENCE", "statute_candidates": ["BSA"], "matched_concepts": ["electronic records"], "weight": 2.0}
        ]

        res1 = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        res2 = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)
        res3 = self.preserver.preserve_and_fuse(query, branch_results, issues, top_k=5)

        self.assertEqual(
            [(r["statute"], r["section"], r["score"]) for r in res1],
            [(r["statute"], r["section"], r["score"]) for r in res2]
        )
        self.assertEqual(
            [(r["statute"], r["section"], r["score"]) for r in res2],
            [(r["statute"], r["section"], r["score"]) for r in res3]
        )

if __name__ == "__main__":
    unittest.main()
