# test_app_endpoints.py — Verify all FastAPI web & API endpoints for Nyaya Darshan

import sys
import unittest
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app


class TestAppEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_01_health_check(self):
        """GET /health -> Status 200 OK."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertGreaterEqual(data["corpus_loaded_sections"], 1200)

    def test_02_dual_panel_query_api(self):
        """POST /api/v1/query -> Status 200 OK with evidence pack."""
        payload = {"query": "Explain the repeal and replacement of CrPC by BNSS 2023."}
        res = self.client.post("/api/v1/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("grounding_status", data)
        self.assertIn("retrieved_sections", data)

    def test_03_chat_router(self):
        """Chat rejects anonymous clients and supports authenticated legal queries."""
        payload = {"query": "What is the penalty for murder under BNS Section 103?"}
        self.assertEqual(self.client.post("/api/chat/ask", json=payload).status_code, 401)
        credentials = {"email": f"chat-{uuid.uuid4().hex[:12]}@example.com", "password": "StrongPassword2026!"}
        registration = self.client.post("/api/auth/register", json={**credentials, "full_name": "Chat Security Test"})
        self.assertEqual(registration.status_code, 201, registration.text)
        login = self.client.post("/api/auth/login", json=credentials)
        self.assertEqual(login.status_code, 200, login.text)
        res = self.client.post("/api/chat/ask", json=payload, headers={"Authorization": f"Bearer {login.json()['access_token']}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)
        self.assertIn("reasoning_steps", data)

    def test_04_frontend_static_serve(self):
        """GET / -> Status 200 OK serving index.html."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
