"""Regression tests for model lifecycle, fallback, and degraded-state handling."""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app import config
from app.intelligence import ai_provider
from app.intelligence.ai_provider import (
    AIProviderUnavailable,
    complete_text,
    get_ai_status,
    reset_ai_provider_state,
)
from app.routers import dashboard


class StatusFailure(RuntimeError):
    def __init__(self, status_code: int):
        super().__init__(f"provider status {status_code}")
        self.status_code = status_code


class TestAIProvider(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reset_ai_provider_state()
        self.api_key_patch = patch.dict(os.environ, {"NVIDIA_API_KEY": "secret-test-key"})
        self.api_key_patch.start()
        self.addCleanup(self.api_key_patch.stop)
        self.addCleanup(reset_ai_provider_state)

    def _route_patches(self):
        return (
            patch.object(config, "AI_MODEL", "nvidia/test-primary"),
            patch.object(config, "AI_FALLBACK_MODELS", ("nvidia/test-fallback",)),
            patch.object(config, "AI_MAX_RETRIES", 0),
            patch.object(
                config,
                "get_llm_client_kwargs",
                return_value={"api_key": "secret-test-key", "base_url": "https://example.invalid/v1"},
            ),
        )

    async def test_lifecycle_failure_activates_configured_fallback(self):
        calls = []

        async def fake_completion(**kwargs):
            calls.append(kwargs["model"])
            if kwargs["model"] == "nvidia/test-primary":
                raise StatusFailure(410)
            return "Grounded fallback answer"

        patches = self._route_patches()
        with patches[0], patches[1], patches[2], patches[3], patch.object(
            ai_provider, "_sdk_completion", new_callable=AsyncMock, side_effect=fake_completion
        ):
            result = await complete_text(
                [{"role": "user", "content": "Question"}],
                max_tokens=32,
                purpose="test",
            )

        self.assertEqual(calls, ["nvidia/test-primary", "nvidia/test-fallback"])
        self.assertEqual(result.model, "nvidia/test-fallback")
        self.assertTrue(result.fallback_used)
        self.assertEqual(get_ai_status()["status"], "degraded")
        self.assertEqual(get_ai_status()["last_error_code"], "HTTP_410")

    async def test_authentication_failure_does_not_try_another_model(self):
        patches = self._route_patches()
        failing_call = AsyncMock(side_effect=StatusFailure(401))
        with patches[0], patches[1], patches[2], patches[3], patch.object(
            ai_provider, "_sdk_completion", failing_call
        ):
            with self.assertRaisesRegex(AIProviderUnavailable, "credentials"):
                await complete_text(
                    [{"role": "user", "content": "Question"}],
                    max_tokens=32,
                )

        self.assertEqual(failing_call.await_count, 1)
        self.assertEqual(get_ai_status()["status"], "unavailable")
        self.assertEqual(get_ai_status()["last_error_code"], "HTTP_401")

    async def test_all_model_failures_surface_unavailable_state(self):
        async def fake_completion(**kwargs):
            status = 410 if kwargs["model"] == "nvidia/test-primary" else 503
            raise StatusFailure(status)

        patches = self._route_patches()
        with patches[0], patches[1], patches[2], patches[3], patch.object(
            ai_provider, "_sdk_completion", new_callable=AsyncMock, side_effect=fake_completion
        ):
            with self.assertRaises(AIProviderUnavailable):
                await complete_text(
                    [{"role": "user", "content": "Question"}],
                    max_tokens=32,
                )

        status = get_ai_status()
        self.assertEqual(status["status"], "unavailable")
        self.assertEqual(status["last_error_code"], "HTTP_503")
        self.assertIsNone(status["active_model"])

    async def test_dashboard_returns_503_instead_of_silent_200(self):
        dashboard._briefing_cache.update({"data": None, "time": 0, "status": None, "model": None})

        class FakeDatabase:
            @staticmethod
            def get_document_stats(organization_id):
                return {"organization": organization_id, "documents": 2}

        with patch.object(
            dashboard,
            "complete_text",
            new_callable=AsyncMock,
            side_effect=AIProviderUnavailable("The AI provider is temporarily unavailable."),
        ):
            response = await dashboard.get_briefing(
                FakeDatabase(),
                {"organization": {"id": "personal-user-1"}},
            )

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.body)
        self.assertEqual(payload["status"], "degraded")
        self.assertIsNone(payload["briefing"])

    def test_known_retired_hosted_models_are_rejected(self):
        with patch.object(config, "AI_BASE_URL", "https://integrate.api.nvidia.com/v1"), patch.object(
            config, "AI_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1.5"
        ), patch.object(config, "AI_FALLBACK_MODELS", ()): 
            with self.assertRaisesRegex(RuntimeError, "end of life"):
                config.validate_ai_model_configuration()

    def test_health_snapshot_never_contains_provider_credentials(self):
        with patch.dict("os.environ", {"NVIDIA_API_KEY": "never-expose-this-secret"}):
            snapshot = get_ai_status()
        self.assertTrue(snapshot["configured"])
        self.assertNotIn("never-expose-this-secret", json.dumps(snapshot))


if __name__ == "__main__":
    unittest.main()
