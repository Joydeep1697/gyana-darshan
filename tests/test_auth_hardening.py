"""Focused authentication security checks for Nyaya Darshan."""

import os
import unittest
from datetime import timedelta
from unittest.mock import patch

from api.auth.service import (
    AuthService,
    create_jwt_token,
    decode_jwt_token,
    get_jwt_secret_key,
)


class TestAuthenticationHardening(unittest.TestCase):
    def test_first_public_registration_does_not_become_superadmin(self):
        expected_user = {"id": "user-1", "email": "first@example.com", "role": "USER"}
        with patch("api.auth.service.UserRepository.get_by_email", return_value=None), patch(
            "api.auth.service.hash_password", return_value="hashed-password"
        ), patch(
            "api.auth.service.UserRepository.create_user", return_value=expected_user
        ) as create_user:
            user, error = AuthService.register_user(
                "first@example.com", "strong-password", "First User"
            )

        self.assertIsNone(error)
        self.assertEqual(user["role"], "USER")
        self.assertEqual(create_user.call_args.args[-1], "USER")

    def test_production_rejects_missing_jwt_secret(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}), patch.dict(
            os.environ, {}, clear=False
        ):
            os.environ.pop("NYAYA_JWT_SECRET", None)
            with self.assertRaisesRegex(RuntimeError, "NYAYA_JWT_SECRET"):
                get_jwt_secret_key()

    def test_tampered_jwt_signature_is_rejected(self):
        token = create_jwt_token({"sub": "test-user"}, timedelta(minutes=5))
        signature = token.rsplit(".", 1)[1]
        replacement = "A" if signature[0] != "A" else "B"
        tampered = token.rsplit(".", 1)[0] + "." + replacement + signature[1:]

        self.assertEqual(decode_jwt_token(token)["sub"], "test-user")
        self.assertIsNone(decode_jwt_token(tampered))


if __name__ == "__main__":
    unittest.main()
