"""Razorpay checkout authentication, price integrity, signatures, and replay tests."""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth.dependencies import get_current_user
from app.routers import billing


class BillingSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "billing.sqlite3")
        self.user = {"id": "user-one", "email": "one@example.test"}

        @contextmanager
        def test_connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        self.connection_patch = patch.object(billing, "get_db_connection", test_connection)
        self.connection_patch.start()
        self.environment_patch = patch.dict(
            os.environ,
            {"RAZORPAY_KEY_ID": "rzp_test_public", "RAZORPAY_KEY_SECRET": "test-secret-only"},
        )
        self.environment_patch.start()
        app = FastAPI()
        app.include_router(billing.router, prefix="/api/billing")
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def tearDown(self):
        self.environment_patch.stop()
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def _create_order(self, order_id="order_123456", plan="Professional"):
        response = Mock()
        response.json.return_value = {
            "id": order_id,
            "amount": billing.PLANS[plan],
            "currency": "INR",
        }
        with patch.object(billing.requests, "post", return_value=response) as post:
            result = self.client.post("/api/billing/orders", json={"plan": plan, "amount": 1})
        return result, post

    @staticmethod
    def _signed(order_id="order_123456", payment_id="pay_123456"):
        signature = hmac.new(
            b"test-secret-only", f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()
        return {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }

    def test_public_config_never_exposes_secret(self):
        response = self.client.get("/api/billing/config")
        self.assertTrue(response.json()["enabled"])
        self.assertNotIn("test-secret-only", response.text)

    def test_server_sets_price_and_rejects_unknown_plan(self):
        response, post = self._create_order()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["amount"], 399900)
        self.assertEqual(post.call_args.kwargs["json"]["amount"], 399900)
        rejected = self.client.post("/api/billing/orders", json={"plan": "FreeForever"})
        self.assertEqual(rejected.status_code, 422)

    def test_valid_signature_is_verified_and_idempotent(self):
        self._create_order()
        inactive = self.client.get("/api/billing/subscription")
        self.assertEqual(inactive.json()["plan"], "Free")
        payload = self._signed()
        first = self.client.post("/api/billing/verify", json=payload)
        second = self.client.post("/api/billing/verify", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["verified"])
        self.assertEqual(second.status_code, 200)
        activated = self.client.get("/api/billing/subscription")
        self.assertEqual(activated.json()["plan"], "Professional")
        self.assertTrue(activated.json()["active"])

    def test_invalid_signature_is_rejected(self):
        self._create_order()
        payload = self._signed()
        payload["razorpay_signature"] = "0" * 64
        response = self.client.post("/api/billing/verify", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_order_cannot_be_verified_by_another_user(self):
        self._create_order()
        self.user = {"id": "user-two", "email": "two@example.test"}
        response = self.client.post("/api/billing/verify", json=self._signed())
        self.assertEqual(response.status_code, 404)

    def test_payment_id_cannot_be_replayed_against_another_order(self):
        self._create_order("order_123456")
        self._create_order("order_789012")
        first = self.client.post("/api/billing/verify", json=self._signed("order_123456"))
        replay = self.client.post("/api/billing/verify", json=self._signed("order_789012"))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 409)

    def test_missing_payment_configuration_fails_closed(self):
        with patch.dict(os.environ, {"RAZORPAY_KEY_SECRET": ""}):
            response = self.client.post("/api/billing/orders", json={"plan": "Professional"})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
