"""Tests for evidence-grounded Nyaya Darshan legal answer generation."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.intelligence.legal_generation import (
    LegalGenerationError,
    generate_grounded_legal_answer,
)


class TestLegalGeneration(unittest.IsolatedAsyncioTestCase):
    async def test_development_without_credentials_returns_labeled_evidence(self):
        with patch("app.intelligence.legal_generation.config.IS_PRODUCTION", False), patch(
            "app.intelligence.legal_generation.config.get_llm_client_kwargs",
            side_effect=RuntimeError("NVIDIA_API_KEY is required"),
        ):
            answer = await generate_grounded_legal_answer(
                "What does BNS Section 103 cover?",
                "BNS Section 103: punishment for murder",
            )

        self.assertIn("AI-generated analysis is unavailable", answer)
        self.assertIn("BNS Section 103: punishment for murder", answer)

    async def test_production_without_credentials_fails_closed(self):
        with patch("app.intelligence.legal_generation.config.IS_PRODUCTION", True), patch(
            "app.intelligence.legal_generation.config.get_llm_client_kwargs",
            side_effect=RuntimeError("NVIDIA_API_KEY is required"),
        ):
            with self.assertRaisesRegex(LegalGenerationError, "not configured"):
                await generate_grounded_legal_answer("Question", "Evidence")

    async def test_cloud_model_receives_question_and_authoritative_evidence(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="BNS Section 103 applies."))]
        )
        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=completion)

        with patch(
            "app.intelligence.legal_generation.config.get_llm_client_kwargs",
            return_value={"api_key": "test-key", "base_url": "https://example.invalid/v1"},
        ), patch(
            "app.intelligence.legal_generation.AsyncOpenAI", return_value=fake_client
        ):
            answer = await generate_grounded_legal_answer(
                "What does BNS Section 103 cover?",
                "BNS Section 103: punishment for murder",
            )

        self.assertEqual(answer, "BNS Section 103 applies.")
        request = fake_client.chat.completions.create.await_args.kwargs
        self.assertIn("BNS Section 103: punishment for murder", request["messages"][1]["content"])
        self.assertIn("What does BNS Section 103 cover?", request["messages"][1]["content"])

    async def test_broken_sdk_falls_back_to_standard_https(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("broken local SDK"))
        with patch(
            "app.intelligence.legal_generation.config.get_llm_client_kwargs",
            return_value={"api_key": "test-key", "base_url": "https://example.invalid/v1"},
        ), patch(
            "app.intelligence.legal_generation.AsyncOpenAI", return_value=fake_client
        ), patch(
            "app.intelligence.legal_generation._generate_with_standard_http",
            new_callable=AsyncMock,
            return_value="BNSS Section 173 governs initial FIR registration.",
        ) as fallback:
            answer = await generate_grounded_legal_answer(
                "What penalty does BNS Section 103 prescribe?",
                "BNS Section 103: punishment for murder",
            )
        self.assertIn("173", answer)
        fallback.assert_awaited_once()

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
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content="POCSO sections 11 and 12 govern non-contact sexual harassment."
            ))]
        )
        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=completion)

        with patch(
            "app.intelligence.legal_generation.config.get_llm_client_kwargs",
            return_value={"api_key": "test-key", "base_url": "https://example.invalid/v1"},
        ), patch(
            "app.intelligence.legal_generation.AsyncOpenAI", return_value=fake_client
        ):
            answer = await generate_grounded_legal_answer(query, evidence)

        request = fake_client.chat.completions.create.await_args.kwargs
        self.assertGreater(request["max_tokens"], 320)
        self.assertIn("Address EVERY numbered question", request["messages"][1]["content"])
        self.assertIn("POCSO section 19", answer)
        self.assertIn("BNSS section 173", answer)
        self.assertIn("BSA section 63", answer)
        self.assertIn("not established guilt", answer)
        self.assertIn("Do not reveal internal category names", request["messages"][1]["content"])

    async def test_missing_source_is_not_invented_to_complete_an_answer(self):
        query = "A 17-year-old received sexually explicit messages, was never touched, and her teacher delayed reporting."
        evidence = "AUTHORITATIVE STATUTORY EXCERPTS:\n- POCSO section 11: Sexual harassment."
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="POCSO section 11 may apply."))]
        )
        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=completion)

        with patch(
            "app.intelligence.legal_generation.config.get_llm_client_kwargs",
            return_value={"api_key": "test-key", "base_url": "https://example.invalid/v1"},
        ), patch(
            "app.intelligence.legal_generation.AsyncOpenAI", return_value=fake_client
        ):
            answer = await generate_grounded_legal_answer(query, evidence)

        self.assertNotIn("POCSO section 12", answer)
        self.assertNotIn("POCSO section 19", answer)
        self.assertNotIn("POCSO section 21", answer)


if __name__ == "__main__":
    unittest.main()
