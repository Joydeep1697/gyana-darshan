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
            "ENVIRONMENT": "production", "LLM_PROVIDER": "nvidia",
            "NYAYA_API_KEY": "a" * 48, "NYAYA_JWT_SECRET": "b" * 48,
            "NVIDIA_API_KEY": "nvapi-" + "c" * 48,
            "ALLOWED_ORIGINS": "https://nyayadarshana.com",
            "RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": "",
            "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "", "GOOGLE_REDIRECT_URI": "",
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


if __name__ == "__main__":
    unittest.main()
