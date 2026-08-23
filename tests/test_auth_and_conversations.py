# test_auth_and_conversations.py — Comprehensive Test Suite for Auth & Conversation Product APIs

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.append(r"d:\Nova Legal")
from api.main import app
from database.connection import init_db

class TestAuthAndConversations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_registration_and_login_flow(self):
        import uuid
        uid = uuid.uuid4().hex[:8]
        email = f"advocate_test_{uid}@nyayadarshana.com".lower()
        password = "SecurePassword2026!"
        full_name = "Adv. Ramesh Sharma"

        # 1. Register
        reg_res = self.client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name
        })
        self.assertEqual(reg_res.status_code, 201, reg_res.text)
        self.assertEqual(reg_res.json()["status"], "SUCCESS")

        # 2. Duplicate registration rejection
        dup_res = self.client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name
        })
        self.assertEqual(dup_res.status_code, 400)

        # 3. Login
        login_res = self.client.post("/api/auth/login", json={
            "email": email,
            "password": password
        })
        self.assertEqual(login_res.status_code, 200, login_res.text)
        tokens = login_res.json()
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)
        self.assertEqual(tokens["token_type"], "bearer")

        # 4. Profile /me
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me_res = self.client.get("/api/auth/me", headers=auth_headers)
        self.assertEqual(me_res.status_code, 200)
        profile = me_res.json()
        self.assertEqual(profile["email"], email)
        self.assertGreaterEqual(profile["daily_quota_remaining"], 0)

        # 5. Refresh token
        ref_res = self.client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        self.assertEqual(ref_res.status_code, 200)
        self.assertIn("access_token", ref_res.json())

    def test_02_conversation_and_evidence_persistence_flow(self):
        import uuid
        uid = uuid.uuid4().hex[:8]
        email = f"consultation_{uid}@nyayadarshana.com"
        password = "SecurePassword2026!"
        
        self.client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Adv. Sunita Rao"
        })
        login_res = self.client.post("/api/auth/login", json={"email": email, "password": password})
        tokens = login_res.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # 1. Create conversation
        conv_res = self.client.post("/api/conversations", json={"title": "NDPS & Bail Analysis"}, headers=headers)
        self.assertEqual(conv_res.status_code, 201, conv_res.text)
        conv = conv_res.json()
        conv_id = conv["id"]
        self.assertEqual(conv["title"], "NDPS & Bail Analysis")
        self.assertEqual(conv["group_period"], "Today")

        # 2. Send legal inquiry
        msg_res = self.client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "What is the procedure and timeline for default bail under BNSS Section 187?", "top_k": 4},
            headers=headers
        )
        self.assertEqual(msg_res.status_code, 200, msg_res.text)
        msg_data = msg_res.json()
        self.assertEqual(msg_data["role"], "assistant")
        self.assertIn("187", msg_data["answer"])
        self.assertGreaterEqual(len(msg_data["evidence"]), 1)
        self.assertEqual(msg_data["engine_version"], "1.0.0")
        self.assertEqual(msg_data["corpus_version"], "2026.08.18")

        # 3. Retrieve conversation history with attached persistent evidence
        history_res = self.client.get(f"/api/conversations/{conv_id}", headers=headers)
        self.assertEqual(history_res.status_code, 200)
        detail = history_res.json()
        self.assertEqual(len(detail["messages"]), 2) # 1 user + 1 assistant
        user_msg = detail["messages"][0]
        asst_msg = detail["messages"][1]
        self.assertEqual(user_msg["role"], "user")
        self.assertEqual(asst_msg["role"], "assistant")
        self.assertIsNotNone(asst_msg["legal_answer"])
        self.assertGreaterEqual(len(asst_msg["legal_answer"]["evidence"]), 1)
        first_ev = asst_msg["legal_answer"]["evidence"][0]
        self.assertTrue(bool(first_ev["statute"]))
        self.assertTrue(bool(first_ev["section"]))
        self.assertTrue(bool(first_ev["source"]))

        # 4. Update title
        patch_res = self.client.patch(
            f"/api/conversations/{conv_id}",
            json={"title": "BNSS 187 Default Bail — Final Brief"},
            headers=headers
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["title"], "BNSS 187 Default Bail — Final Brief")

        # 5. List conversations
        list_res = self.client.get("/api/conversations", headers=headers)
        self.assertEqual(list_res.status_code, 200)
        convs = list_res.json()
        self.assertGreaterEqual(len(convs), 1)
        self.assertEqual(convs[0]["id"], conv_id)

        # 6. Delete conversation
        del_res = self.client.delete(f"/api/conversations/{conv_id}", headers=headers)
        self.assertEqual(del_res.status_code, 204)

        # Verify deleted
        get_del_res = self.client.get(f"/api/conversations/{conv_id}", headers=headers)
        self.assertEqual(get_del_res.status_code, 404)

if __name__ == "__main__":
    unittest.main()
