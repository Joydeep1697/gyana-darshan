"""Regression tests for legal scenarios that previously produced unsafe answers."""

import unittest

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from retrieval.legal_reasoning import build_reasoning_plan, deterministic_grounded_answer


class AdversarialReasoningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = AuthoritativeLegalRetriever()

    def assert_sections(self, query, required, excluded=()):
        pack = self.retriever.retrieve_evidence_pack(query, top_k=4)
        found = {
            (item.get("short_name", "").upper(), str(item.get("section", "")).split("(")[0])
            for item in pack["retrieved_sections"]
        }
        for citation in required:
            self.assertIn(citation, found, (query, found))
        for citation in excluded:
            self.assertNotIn(citation, found, (query, found))

    def test_pre_commencement_offence_uses_savings(self):
        query = "A theft occurred on 29 June 2024 but the FIR and trial began after 1 July 2024. Which law governs?"
        plan = build_reasoning_plan(query)
        self.assertEqual(plan.offence_date.isoformat(), "2024-06-29")
        self.assert_sections(query, {("BNS", "358"), ("BNSS", "531")})

    def test_default_bail_uses_bnss_187(self):
        self.assert_sections(
            "The accused applied for default bail on day 91 before the charge sheet. Which section applies?",
            {("BNSS", "187")}, {("BNSS", "479")},
        )

    def test_non_contact_pocso_uses_harassment_sections(self):
        self.assert_sections(
            "An adult sent sexually explicit messages to a 15-year-old online; they never met and there was no physical contact.",
            {("POCSO", "11"), ("POCSO", "12")},
            {("POCSO", "3"), ("POCSO", "4"), ("POCSO", "5"), ("POCSO", "6")},
        )

    def test_entrusted_money_is_breach_of_trust(self):
        self.assert_sections(
            "A cashier lawfully receives entrusted money and later diverts it. Is this theft?",
            {("BNS", "316")},
        )

    def test_zero_fir_uses_bnss_173(self):
        self.assert_sections(
            "Can the nearest police station refuse a cognizable FIR because it occurred in another district?",
            {("BNSS", "173")},
        )

    def test_transition_question_is_answered_without_cloud_model(self):
        query = "A theft occurred on 29 June 2024 but the FIR was registered on 3 July 2024. Does BNS section 303 apply?"
        pack = self.retriever.retrieve_evidence_pack(query, top_k=4)
        answer = deterministic_grounded_answer(query, self.retriever.format_evidence_context(pack))
        self.assertIsNotNone(answer)
        self.assertIn("Indian Penal Code (IPC)", answer)
        self.assertIn("BNS section 358", answer)
        self.assertIn("BNSS section 531", answer)

    def test_custody_arithmetic_distinguishes_limits(self):
        plan = build_reasoning_plan(
            "For an offence punishable with life imprisonment, the accused already spent 12 days in police custody. How much police custody remains?"
        )
        safeguards = " ".join(plan.safeguards)
        self.assertIn("maximum additional police custody is 3 days", safeguards)
        self.assertIn("90 days", safeguards)

    def test_electronic_record_uses_bsa_62_and_63(self):
        self.assert_sections(
            "Are WhatsApp screenshots and a chat backup admissible electronic evidence without a certificate?",
            {("BSA", "62"), ("BSA", "63")},
        )


if __name__ == "__main__":
    unittest.main()
