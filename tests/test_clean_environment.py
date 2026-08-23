# test_clean_environment.py — Production Readiness Clean Environment & Smoke Validation
#
# Validates:
# 1. Fresh application startup & lifespan initialization
# 2. Database table presence and WAL mode
# 3. Corpus availability & section count
# 4. API accessibility & health endpoint response structure
# 5. Missing environment variable behavior
# 6. Retrieval query execution & evidence schema
# 7. Invalid request rejection (RFC-7807)
# 8. Path exposure and trace sanitization

import os
import sys
import json
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app as web_app
from api.main import app as api_app
from api.security import LEAK_PATTERNS


class TestCleanEnvironment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(web_app, raise_server_exceptions=False)
        cls.api_client = TestClient(api_app, raise_server_exceptions=False)

    def test_01_health_endpoint(self):
        """Verify health check endpoint returns 200 and expected schema."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertGreaterEqual(data["corpus_loaded_sections"], 1200)

    def test_02_database_initialization(self):
        """Verify SQLite database is initialized with WAL mode and tables exist."""
        from database.connection import get_sqlite_conn
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        row = cursor.fetchone()
        self.assertEqual(row[0].lower(), "wal")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        self.assertIn("users", tables)
        self.assertIn("conversations", tables)
        self.assertIn("messages", tables)
        conn.close()

    def test_03_query_pipeline_and_evidence(self):
        """Verify statutory retrieval and dual-panel evidence contract."""
        payload = {
            "query": "What is the punishment for murder under BNS?",
            "top_k": 3
        }
        res = self.api_client.post("/api/v1/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("retrieved_sections", data)
        self.assertIn("verification_firewall", data)
        self.assertIn("grounding_status", data)
        self.assertGreater(len(data["retrieved_sections"]), 0)

        # Check path leakage in the full JSON response
        raw_json = json.dumps(data)
        for pat in LEAK_PATTERNS:
            import re
            matches = re.findall(pat, raw_json, re.IGNORECASE)
            self.assertEqual(len(matches), 0, f"Leaked pattern '{pat}' in response: {matches}")

    def test_04_invalid_request_handling(self):
        """Verify invalid requests return 422 with sanitized details."""
        # Empty string
        res = self.api_client.post("/api/v1/query", json={"query": ""})
        self.assertEqual(res.status_code, 422)

        # Oversized top_k
        res = self.api_client.post("/api/v1/query", json={"query": "Valid", "top_k": 999})
        self.assertEqual(res.status_code, 422)

    def test_05_missing_env_behavior(self):
        """Verify that missing required NVIDIA_API_KEY raises RuntimeError when provider is nvidia."""
        from app.config import get_llm_client_kwargs
        orig_key = os.environ.get("NVIDIA_API_KEY")
        try:
            if "NVIDIA_API_KEY" in os.environ:
                del os.environ["NVIDIA_API_KEY"]
            import app.config as cfg
            orig_provider = cfg.LLM_PROVIDER
            cfg.LLM_PROVIDER = "nvidia"
            with self.assertRaises(RuntimeError):
                get_llm_client_kwargs()
            cfg.LLM_PROVIDER = orig_provider
        finally:
            if orig_key is not None:
                os.environ["NVIDIA_API_KEY"] = orig_key


if __name__ == "__main__":
    unittest.main()
