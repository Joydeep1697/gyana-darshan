"""Dependency-light release checks for the authoritative statutory corpus."""

import unittest

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever


class TestStatutoryReleaseGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = AuthoritativeLegalRetriever()

    def assert_section_retrieved(self, query, expected_statute, expected_section):
        evidence = self.retriever.retrieve_evidence_pack(query, top_k=5)
        actual = [
            (
                record.get("short_name", record.get("statute", "")),
                str(record.get("section", "")).split("(")[0],
            )
            for record in evidence.get("retrieved_sections", [])
        ]
        self.assertTrue(
            any(expected_statute in statute and section == expected_section for statute, section in actual),
            f"Expected {expected_statute} section {expected_section}; retrieved {actual}",
        )

    def test_statutory_corpus_contains_expected_sections(self):
        self.assertGreaterEqual(len(self.retriever.corpus), 1200)

    def test_bns_murder_section_is_retrieved(self):
        self.assert_section_retrieved(
            "What is the punishment for murder under BNS Section 103?", "BNS", "103"
        )

    def test_bnss_custody_section_is_retrieved(self):
        self.assert_section_retrieved(
            "Explain police custody and remand under BNSS Section 187", "BNSS", "187"
        )

    def test_bsa_electronic_evidence_section_is_retrieved(self):
        self.assert_section_retrieved(
            "How are electronic records admitted under BSA Section 63?", "BSA", "63"
        )


if __name__ == "__main__":
    unittest.main()
