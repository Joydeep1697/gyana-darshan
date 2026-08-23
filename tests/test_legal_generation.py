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


if __name__ == "__main__":
    unittest.main()
