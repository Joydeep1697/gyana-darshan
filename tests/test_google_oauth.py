"""Configuration and request-safety checks for optional Google sign-in."""

import os
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from api.auth.google_oauth import google_authorization_url, google_oauth_enabled


class GoogleOAuthTests(unittest.TestCase):
    def test_google_login_is_disabled_without_credentials(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
            self.assertFalse(google_oauth_enabled())

    def test_google_login_requests_only_identity_scopes(self):
        credentials = {
            "GOOGLE_CLIENT_ID": "example.apps.googleusercontent.com",
            "GOOGLE_CLIENT_SECRET": "example-secret",
            "GOOGLE_REDIRECT_URI": "http://127.0.0.1:8000/api/auth/google/callback",
        }
        with patch.dict(os.environ, credentials):
            self.assertTrue(google_oauth_enabled())
            url = urlparse(google_authorization_url("opaque-csrf-state"))
            params = parse_qs(url.query)
            self.assertEqual(url.netloc, "accounts.google.com")
            self.assertEqual(params["scope"], ["openid email profile"])
            self.assertEqual(params["state"], ["opaque-csrf-state"])
            self.assertEqual(params["redirect_uri"], [credentials["GOOGLE_REDIRECT_URI"]])
            self.assertNotIn("client_secret", params)


if __name__ == "__main__":
    unittest.main()
