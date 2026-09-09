"""Configuration and request-safety checks for optional Google sign-in."""

import os
import unittest
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError
from unittest.mock import patch

from api.auth.google_oauth import GoogleOAuthError, exchange_google_code, google_authorization_url, google_oauth_enabled


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

    def test_google_token_exchange_reports_sanitized_provider_error(self):
        credentials = {
            "GOOGLE_CLIENT_ID": "example.apps.googleusercontent.com",
            "GOOGLE_CLIENT_SECRET": "example-secret",
            "GOOGLE_REDIRECT_URI": "http://127.0.0.1:8000/api/auth/google/callback",
        }
        error_body = b'{"error":"invalid_grant","error_description":"Bad Request"}'
        http_error = HTTPError(
            "https://oauth2.googleapis.com/token",
            400,
            "Bad Request",
            {},
            fp=_Bytes(error_body),
        )
        with patch.dict(os.environ, credentials), patch("api.auth.google_oauth.urlopen", side_effect=http_error):
            with self.assertRaisesRegex(
                GoogleOAuthError,
                "Google token exchange failed: invalid_grant - Bad Request",
            ) as caught:
                exchange_google_code("single-use-code")
        self.assertNotIn("example-secret", str(caught.exception))
        self.assertNotIn("single-use-code", str(caught.exception))


class _Bytes:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


if __name__ == "__main__":
    unittest.main()
