"""Tests for evidence-grounded Nyaya Darshan legal answer generation."""

import unittest
from unittest.mock import AsyncMock, patch

from app.intelligence.ai_provider import (
    AICompletion,
    AIConfigurationError,
    AIProviderUnavailable,
)
from app.intelligence import legal_generation as generation_module

from app.intelligence.legal_generation import (
    LegalGenerationError,
    generate_grounded_legal_answer,
)


class TestLegalGeneration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        generation_module._cache.clear()

    async def test_development_without_credentials_returns_labeled_evidence(self):
        with patch("app.intelligence.legal_generation.config.IS_PRODUCTION", False), patch(
            "app.intelligence.legal_generation.complete_text",
            new_callable=AsyncMock,
            side_effect=AIConfigurationError("not configured"),
        ):
            answer = await generate_grounded_legal_answer(
                "What does BNS Section 103 cover?",
                "BNS Section 103: punishment for murder",
            )

        self.assertIn("AI-generated analysis is unavailable", answer)
        self.assertIn("BNS Section 103: punishment for murder", answer)

    async def test_production_without_credentials_fails_closed(self):
        with patch("app.intelligence.legal_generation.config.IS_PRODUCTION", True), patch(
            "app.intelligence.legal_generation.complete_text",
            new_callable=AsyncMock,
            side_effect=AIConfigurationError("not configured"),
        ):
            with self.assertRaisesRegex(LegalGenerationError, "not configured"):
                await generate_grounded_legal_answer("Question", "Evidence")

    async def test_cloud_model_receives_question_and_authoritative_evidence(self):
        with patch(
            "app.intelligence.legal_generation.complete_text",
            new_callable=AsyncMock,
            return_value=AICompletion(
                content="BNS Section 103 applies.",
                model="nvidia/test-primary",
                fallback_used=False,
            ),
        ) as provider:
            answer = await generate_grounded_legal_answer(
                "What does BNS Section 103 cover?",
                "BNS Section 103: punishment for murder",
            )

        self.assertEqual(answer, "BNS Section 103 applies.")
        request = provider.await_args
        self.assertIn("BNS Section 103: punishment for murder", request.args[0][1]["content"])
        self.assertIn("What does BNS Section 103 cover?", request.args[0][1]["content"])

    async def test_provider_outage_becomes_service_error(self):
        with patch(
            "app.intelligence.legal_generation.complete_text",
            new_callable=AsyncMock,
            side_effect=AIProviderUnavailable("The AI provider is temporarily unavailable."),
        ):
            with self.assertRaisesRegex(LegalGenerationError, "temporarily unavailable"):
                await generate_grounded_legal_answer(
                    "What penalty does BNS Section 103 prescribe?",
                    "BNS Section 103: punishment for murder",
                )

    async def test_complex_scenario_uses_cloud_and_expanded_token_budget(self):
        query = (
            "A 17-year-old student receives sexually explicit messages from an adult who "
            "never touched her and is threatening to publish intimate images. The teacher "
            "delayed reporting, police registered the FIR electronically, and screenshots "
            "are said to prove guilt. Analyze consent, reporting, threats, FIR procedure, "
            "electronic evidence, and whether the facts alone conclusively establish guilt."
        )
        evidence = (
            "AUTHORITATIVE STATUTORY EXCERPTS:\n"
            "- POCSO section 11: Sexual harassment.\n"
            "- POCSO section 12: Punishment for sexual harassment.\n"
            "- POCSO section 19: Reporting.\n"
            "- POCSO section 21: Failure to report.\n"
            "- POCSO section 2: Child means a person below 18.\n"
            "- BSA section 63: Electronic records.\n"
            "- BSA section 62: Proof of electronic records.\n"
            "- BNSS section 173: Information in cognizable cases.\n"
            "- BNS section 308: Extortion.\n"
            "- BNS section 351: Criminal intimidation."
        )
        with patch(
            "app.intelligence.legal_generation.complete_text",
            new_callable=AsyncMock,
            return_value=AICompletion(
                content="POCSO sections 11 and 12 govern non-contact sexual harassment.",
                model="nvidia/test-primary",
                fallback_used=False,
            ),
        ) as provider:
            answer = await generate_grounded_legal_answer(query, evidence)

        request = provider.await_args
        self.assertGreater(request.kwargs["max_tokens"], 320)
        self.assertIn("Address EVERY numbered question", request.args[0][1]["content"])
        self.assertIn("POCSO section 19", answer)
        self.assertIn("BNSS section 173", answer)
        self.assertIn("BSA section 63", answer)
        self.assertIn("not established guilt", answer)
        self.assertIn("Do not reveal internal category names", request.args[0][1]["content"])

    async def test_missing_source_is_not_invented_to_complete_an_answer(self):
        query = "A 17-year-old received sexually explicit messages, was never touched, and her teacher delayed reporting."
        evidence = "AUTHORITATIVE STATUTORY EXCERPTS:\n- POCSO section 11: Sexual harassment."
        with patch(
            "app.intelligence.legal_generation.complete_text",
            new_callable=AsyncMock,
            return_value=AICompletion(
                content="POCSO section 11 may apply.",
                model="nvidia/test-primary",
                fallback_used=False,
            ),
        ):
            answer = await generate_grounded_legal_answer(query, evidence)

        self.assertNotIn("POCSO section 12", answer)
        self.assertNotIn("POCSO section 19", answer)
        self.assertNotIn("POCSO section 21", answer)


if __name__ == "__main__":
    unittest.main()
