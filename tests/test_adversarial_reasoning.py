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
        self.assertIn("no more than 3 aggregate days remain", safeguards)
        self.assertIn("validly authorised", safeguards)
        self.assertIn("90 days", safeguards)

    def test_electronic_record_uses_bsa_62_and_63(self):
        self.assert_sections(
            "Are WhatsApp screenshots and a chat backup admissible electronic evidence without a certificate?",
            {("BSA", "62"), ("BSA", "63")},
        )

    def test_complex_school_scenario_identifies_every_independent_issue(self):
        query = (
            "A 17-year-old student tells her teacher that a 24-year-old man has been sending "
            "her sexually explicit messages on Instagram and threatening to publish edited "
            "intimate images unless she meets him. He says she consented and he never touched "
            "her. The teacher waits five days before reporting. Police register the FIR "
            "electronically and say screenshots are automatically admissible without "
            "verification. Can these facts alone conclusively establish guilt?"
        )
        plan = build_reasoning_plan(query)
        issues = {issue.category for issue in plan.issues}
        self.assertTrue(plan.is_complex)
        self.assertTrue({
            "pocso_non_contact_harassment", "pocso_reporting", "pocso_age_consent",
            "electronic_evidence_current", "electronic_fir_registration", "extortion",
        }.issubset(issues), issues)
        self.assertTrue(any("proof at trial" in value.lower() for value in plan.safeguards))
        reporting = next(issue for issue in plan.issues if issue.category == "pocso_reporting")
        self.assertIn("Do not call delayed reporting automatically punishable", reporting.guidance)
        threats = next(issue for issue in plan.issues if issue.category == "extortion")
        self.assertIn("does not establish that element", threats.guidance)
        self.assert_sections(
            query,
            {
                ("POCSO", "11"), ("POCSO", "12"), ("POCSO", "19"), ("POCSO", "21"),
                ("POCSO", "2"), ("BSA", "62"), ("BSA", "63"), ("BNSS", "173"),
                ("BNS", "308"), ("BNS", "351"),
            },
            {("POCSO", "3"), ("POCSO", "4"), ("POCSO", "7"), ("POCSO", "8")},
        )


if __name__ == "__main__":
    unittest.main()
