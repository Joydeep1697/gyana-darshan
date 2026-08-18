# test_app_endpoints.py — Verify all FastAPI web & API endpoints for Nyaya Darshan

import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("=========================================================================")
    print("=== NYAYA DARSHAN — FULL WEB & API ENDPOINTS INTEGRATION TEST         ===")
    print("=========================================================================")

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[+] GET /health -> Status 200 OK |", res.json())

    # 2. Dual-Panel Grounding API (/api/v1/query)
    q1 = {"query": "Explain the repeal and replacement of CrPC by BNSS 2023."}
    res1 = client.post("/api/v1/query", json=q1)
    assert res1.status_code == 200, f"/api/v1/query failed: {res1.text}"
    data1 = res1.json()
    print("\n[+] POST /api/v1/query -> Status 200 OK")
    print("    Answer:", data1["answer"])
    print("    Grounding Status:", data1["grounding_status"])
    print("    Sections Retrieved:", len(data1["retrieved_sections"]))
    print("    Latency:", data1["latency_ms"], "ms")

    # 3. Chat Router (/api/chat/ask)
    q2 = {"query": "What is the penalty for murder under BNS Section 103?"}
    res2 = client.post("/api/chat/ask", json=q2)
    assert res2.status_code == 200, f"/api/chat/ask failed: {res2.text}"
    data2 = res2.json()
    print("\n[+] POST /api/chat/ask -> Status 200 OK")
    print("    Answer:", data2["answer"])
    print("    Sources Count:", len(data2["sources"]))
    print("    Reasoning Steps:", len(data2["reasoning_steps"]))

    # 4. Frontend static serve (GET /)
    res_root = client.get("/")
    assert res_root.status_code == 200, f"GET / failed: {res_root.status_code}"
    print("\n[+] GET / -> Status 200 OK (Served index.html successfully)")

    print("\n=========================================================================")
    print("=== ALL NYAYA DARSHAN WEB & API ENDPOINTS VERIFIED (100% OPERATIONAL) ===")
    print("=========================================================================")

if __name__ == "__main__":
    test_endpoints()
