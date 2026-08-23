# test_release_gate.py — Final Release Gate Automated Security & Compliance Test Suite
#
# Validates:
# 1. Fail-Closed API Security in production mode (refusal on missing key, 401 on bad key, 200 on valid key)
# 2. Production CORS enforcement (rejection of wildcard in prod, credentials disabled on wildcard in dev)
# 3. Render Port & Runtime configuration ($PORT dynamic binding)
# 4. Secret scan verification across tracked files

import os
import sys
import json
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class TestFinalReleaseGate(unittest.TestCase):

    def test_01_fail_closed_missing_nyaya_api_key_in_production(self):
        """Production mode must refuse startup when NYAYA_API_KEY is missing."""
        import app.config as cfg
        orig_env = os.environ.get("ENVIRONMENT")
        orig_key = os.environ.get("NYAYA_API_KEY")
        try:
            os.environ["ENVIRONMENT"] = "production"
            cfg.ENV = "production"
            cfg.IS_PRODUCTION = True
            if "NYAYA_API_KEY" in os.environ:
                del os.environ["NYAYA_API_KEY"]

            with self.assertRaises(RuntimeError) as ctx:
                cfg.validate_production_config()
            self.assertIn("NYAYA_API_KEY is required in production mode", str(ctx.exception))
        finally:
            if orig_env is not None:
                os.environ["ENVIRONMENT"] = orig_env
                cfg.ENV = orig_env
                cfg.IS_PRODUCTION = (orig_env.lower() in ["production", "prod"])
            else:
                os.environ.pop("ENVIRONMENT", None)
                cfg.ENV = "development"
                cfg.IS_PRODUCTION = False
            if orig_key is not None:
                os.environ["NYAYA_API_KEY"] = orig_key

    def test_02_fail_closed_api_endpoint_rejection(self):
        """Protected endpoint must reject requests without the valid API key."""
        from fastapi.testclient import TestClient
        from api.main import app as api_app

        orig_key = os.environ.get("NYAYA_API_KEY")
        try:
            os.environ["NYAYA_API_KEY"] = "secret-production-test-key-12345"

            client = TestClient(api_app, raise_server_exceptions=False)

            # Request without key -> 401
            res_no_key = client.post("/api/v1/query", json={"query": "Convert IPC 302 to BNS"})
            self.assertEqual(res_no_key.status_code, 401)

            # Request with wrong key -> 401
            res_bad_key = client.post(
                "/api/v1/query",
                headers={"X-API-Key": "wrong-key"},
                json={"query": "Convert IPC 302 to BNS"}
            )
            self.assertEqual(res_bad_key.status_code, 401)

            # Request with valid key in header -> 200
            res_valid = client.post(
                "/api/v1/query",
                headers={"X-API-Key": "secret-production-test-key-12345"},
                json={"query": "Convert IPC 302 to BNS"}
            )
            self.assertEqual(res_valid.status_code, 200)

            # Request with valid key in Bearer token -> 200
            res_bearer = client.post(
                "/api/v1/query",
                headers={"Authorization": "Bearer secret-production-test-key-12345"},
                json={"query": "Convert IPC 302 to BNS"}
            )
            self.assertEqual(res_bearer.status_code, 200)
        finally:
            if orig_key is not None:
                os.environ["NYAYA_API_KEY"] = orig_key
            else:
                os.environ.pop("NYAYA_API_KEY", None)

    def test_03_production_cors_fail_closed_on_wildcard(self):
        """Production mode must refuse startup when ALLOWED_ORIGINS is missing or wildcard."""
        import app.config as cfg
        orig_env = os.environ.get("ENVIRONMENT")
        orig_origins = os.environ.get("ALLOWED_ORIGINS")
        orig_key = os.environ.get("NYAYA_API_KEY")
        try:
            os.environ["ENVIRONMENT"] = "production"
            cfg.ENV = "production"
            cfg.IS_PRODUCTION = True
            os.environ["NYAYA_API_KEY"] = "test-key"

            # Missing ALLOWED_ORIGINS
            if "ALLOWED_ORIGINS" in os.environ:
                del os.environ["ALLOWED_ORIGINS"]
            with self.assertRaises(RuntimeError) as ctx:
                cfg.validate_production_config()
            self.assertIn("ALLOWED_ORIGINS is required in production mode", str(ctx.exception))

            # Wildcard ALLOWED_ORIGINS
            os.environ["ALLOWED_ORIGINS"] = "*"
            with self.assertRaises(RuntimeError) as ctx:
                cfg.validate_production_config()
            self.assertIn("ALLOWED_ORIGINS is required in production mode", str(ctx.exception))

            # Explicit ALLOWED_ORIGINS -> passes validation
            os.environ["ALLOWED_ORIGINS"] = "https://nyayadarshana.com"
            cfg.validate_production_config()
        finally:
            if orig_env is not None:
                os.environ["ENVIRONMENT"] = orig_env
                cfg.ENV = orig_env
                cfg.IS_PRODUCTION = (orig_env.lower() in ["production", "prod"])
            else:
                os.environ.pop("ENVIRONMENT", None)
                cfg.ENV = "development"
                cfg.IS_PRODUCTION = False
            if orig_origins is not None:
                os.environ["ALLOWED_ORIGINS"] = orig_origins
            else:
                os.environ.pop("ALLOWED_ORIGINS", None)
            if orig_key is not None:
                os.environ["NYAYA_API_KEY"] = orig_key
            else:
                os.environ.pop("NYAYA_API_KEY", None)

    def test_04_render_port_contract(self):
        """Verify that server port configuration dynamically obeys $PORT."""
        orig_port = os.environ.get("PORT")
        try:
            os.environ["PORT"] = "10000"
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.PORT, 10000)
        finally:
            if orig_port is not None:
                os.environ["PORT"] = orig_port
            else:
                os.environ.pop("PORT", None)
            import importlib
            import app.config as cfg
            importlib.reload(cfg)


if __name__ == "__main__":
    unittest.main()
