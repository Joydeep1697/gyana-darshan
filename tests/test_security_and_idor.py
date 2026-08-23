# test_security_and_idor.py — Security, IDOR & Multi-Tenant Isolation Test Suite

import sys
import uuid
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.append(r"d:\Gyana Darshan")
from api.main import app
from database.connection import init_db
from database.repository import UserRepository, UsageRepository

class TestSecurityAndIDOR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        # Setup User A
        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@nyayadarshana.com"
        cls.client.post("/api/auth/register", json={
            "email": cls.user_a_email,
            "password": "PasswordUserA123!",
            "full_name": "Advocate User A"
        })
        res_a = cls.client.post("/api/auth/login", json={
            "email": cls.user_a_email,
            "password": "PasswordUserA123!"
        })
        cls.token_a = res_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Setup User B
        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@nyayadarshana.com"
        cls.client.post("/api/auth/register", json={
            "email": cls.user_b_email,
            "password": "PasswordUserB123!",
            "full_name": "Advocate User B"
        })
        res_b = cls.client.post("/api/auth/login", json={
            "email": cls.user_b_email,
            "password": "PasswordUserB123!"
        })
        cls.token_b = res_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    def test_01_unauthenticated_requests_blocked(self):
        """Ensure all protected conversation and profile endpoints strictly reject unauthenticated requests."""
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/conversations").status_code, 401)
        self.assertEqual(self.client.post("/api/conversations", json={"title": "Test"}).status_code, 401)
        self.assertEqual(self.client.get(f"/api/conversations/{uuid.uuid4()}").status_code, 401)
        self.assertEqual(self.client.post(f"/api/conversations/{uuid.uuid4()}/messages", json={"content": "test"}).status_code, 401)

    def test_02_tampered_token_rejected(self):
        """Ensure tampered signature or corrupted JWT is rejected."""
        fake_token = self.token_a[:-5] + "XXXXX"
        fake_headers = {"Authorization": f"Bearer {fake_token}"}
        res = self.client.get("/api/auth/me", headers=fake_headers)
        self.assertEqual(res.status_code, 401)

    def test_03_idor_cross_tenant_access_prevented(self):
        """Verify strict multi-tenant isolation: User B cannot view, edit, post to, or delete User A's consultation."""
        # 1. User A creates conversation
        conv_res = self.client.post("/api/conversations", json={"title": "User A Private Legal Memo"}, headers=self.headers_a)
        self.assertEqual(conv_res.status_code, 201)
        conv_id = conv_res.json()["id"]

        # 2. User B tries to GET User A's conversation
        b_get = self.client.get(f"/api/conversations/{conv_id}", headers=self.headers_b)
        self.assertEqual(b_get.status_code, 404, "User B should not be able to read User A conversation")

        # 3. User B tries to PATCH User A's conversation title
        b_patch = self.client.patch(f"/api/conversations/{conv_id}", json={"title": "Hacked Title"}, headers=self.headers_b)
        self.assertEqual(b_patch.status_code, 404, "User B should not be able to update User A conversation")

        # 4. User B tries to POST a message into User A's conversation
        b_post_msg = self.client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "Malicious injected question", "top_k": 4},
            headers=self.headers_b
        )
        self.assertEqual(b_post_msg.status_code, 404, "User B should not be able to write to User A conversation")

        # 5. User B tries to DELETE User A's conversation
        b_del = self.client.delete(f"/api/conversations/{conv_id}", headers=self.headers_b)
        self.assertEqual(b_del.status_code, 404, "User B should not be able to delete User A conversation")

        # 6. Verify User A's conversation is intact
        a_get = self.client.get(f"/api/conversations/{conv_id}", headers=self.headers_a)
        self.assertEqual(a_get.status_code, 200)
        self.assertEqual(a_get.json()["conversation"]["title"], "User A Private Legal Memo")

    def test_04_user_quota_exhaustion_enforcement(self):
        """Ensure rate quota blocks requests once user daily quota is reached."""
        user_c_email = f"quota_{uuid.uuid4().hex[:8]}@nyayadarshana.com"
        self.client.post("/api/auth/register", json={
            "email": user_c_email,
            "password": "PasswordUserC123!",
            "full_name": "Advocate User C"
        })
        res_c = self.client.post("/api/auth/login", json={"email": user_c_email, "password": "PasswordUserC123!"})
        token_c = res_c.json()["access_token"]
        headers_c = {"Authorization": f"Bearer {token_c}"}

        # Create conversation
        conv = self.client.post("/api/conversations", json={"title": "Quota Test"}, headers=headers_c).json()
        conv_id = conv["id"]

        # Fetch user ID and simulate 100 queries consumed
        user_record = UserRepository.get_by_email(user_c_email)
        for _ in range(100):
            UsageRepository.record_usage(user_record["id"], endpoint="/api/conversations/messages", tokens=1)

        # Next query must be rejected with 429
        over_res = self.client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "Will this succeed?", "top_k": 4},
            headers=headers_c
        )
        self.assertEqual(over_res.status_code, 429)
        self.assertIn("Daily legal consultation quota reached", over_res.json()["detail"])

if __name__ == "__main__":
    unittest.main()
