"""Regression tests for production deployment configuration gates."""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("release_preflight", ROOT / "scripts" / "release_preflight.py")
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class TestDeploymentPreflight(unittest.TestCase):
    def setUp(self):
        environment = {
            "ENVIRONMENT": "production", "AI_PROVIDER": "nvidia",
            "NYAYA_API_KEY": "a" * 48, "NYAYA_JWT_SECRET": "b" * 48,
            "NVIDIA_API_KEY": "nvapi-" + "c" * 48,
            "AI_MODEL": "nvidia/nemotron-3-super-120b-a12b",
            "AI_FALLBACK_MODEL": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "ALLOWED_ORIGINS": "https://nyayadarshana.com",
            "RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": "",
            "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "", "GOOGLE_REDIRECT_URI": "",
            "NYAYA_CREDENTIAL_ROTATION_CONFIRMED": "true",
        }
        self.environment_patch = patch.dict(os.environ, environment)
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)

    def test_valid_production_configuration_passes(self):
        self.assertEqual(preflight.check_environment(), [])

    def test_insecure_origins_are_rejected(self):
        for origin in ("*", "http://nyayadarshana.com", "https://nyayadarshana.com/path"):
            with self.subTest(origin=origin), patch.dict(os.environ, {"ALLOWED_ORIGINS": origin}):
                self.assertTrue(any("ALLOWED_ORIGINS" in issue for issue in preflight.check_environment()))

    def test_partial_payment_credentials_are_rejected(self):
        with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "rzp_test_valid"}):
            self.assertTrue(any("configured together" in issue for issue in preflight.check_environment()))

    def test_short_secrets_are_rejected(self):
        with patch.dict(os.environ, {"NYAYA_JWT_SECRET": "short"}):
            self.assertTrue(any("NYAYA_JWT_SECRET" in issue for issue in preflight.check_environment()))

    def test_retired_hosted_model_is_rejected(self):
        with patch.dict(os.environ, {
            "AI_MODEL": "nvidia/llama-3.3-nemotron-super-49b-v1",
        }):
            self.assertTrue(any("Retired NVIDIA hosted model" in issue for issue in preflight.check_environment()))

    def test_missing_distinct_fallback_is_rejected(self):
        with patch.dict(os.environ, {
            "AI_MODEL": "nvidia/nemotron-3-super-120b-a12b",
            "AI_FALLBACK_MODEL": "nvidia/nemotron-3-super-120b-a12b",
        }):
            self.assertTrue(any("AI_FALLBACK_MODEL" in issue for issue in preflight.check_environment()))

    def test_partial_or_insecure_google_oauth_configuration_is_rejected(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "client-id"}):
            self.assertTrue(any("configured together" in issue for issue in preflight.check_environment()))
        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "client-id",
            "GOOGLE_CLIENT_SECRET": "client-secret",
            "GOOGLE_REDIRECT_URI": "http://nyayadarshana.com/api/auth/google/callback",
        }):
            self.assertTrue(any("GOOGLE_REDIRECT_URI" in issue for issue in preflight.check_environment()))

    def test_repository_configuration_is_complete(self):
        self.assertEqual(preflight.check_repository(), [])

    def test_production_requires_credential_rotation_confirmation(self):
        with patch.dict(os.environ, {"NYAYA_CREDENTIAL_ROTATION_CONFIRMED": ""}):
            self.assertTrue(any("CREDENTIAL_ROTATION" in issue for issue in preflight.check_environment()))

    def test_repository_rejects_tracked_product_hygiene_artifacts(self):
        self.assertTrue(any(pattern.search("evaluation/phase_8_report.json") for pattern in preflight.TRACKED_ARTIFACT_PATTERNS))
        self.assertTrue(any(pattern.search("training/train.jsonl") for pattern in preflight.TRACKED_ARTIFACT_PATTERNS))
        self.assertTrue(any(pattern.search("scratch_debug.py") for pattern in preflight.TRACKED_ARTIFACT_PATTERNS))
        self.assertTrue(any(pattern.search("retrieval/experimental/prototype.py") for pattern in preflight.TRACKED_ARTIFACT_PATTERNS))

    def test_repository_secret_scan_detects_high_confidence_patterns(self):
        examples = {
            "NVIDIA API key": "NVIDIA_API_KEY=nvapi-" + "a" * 32,
            "Razorpay live key": "RAZORPAY_KEY_ID=" + "rzp_" + "live_" + "1234567890",
        }
        for label, value in examples.items():
            with self.subTest(label=label):
                self.assertTrue(preflight.HIGH_CONFIDENCE_SECRET_PATTERNS[label].search(value))


if __name__ == "__main__":
    unittest.main()
