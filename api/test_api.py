# test_api.py — Quick test client for Nyaya Legal OS Production API

import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api():
    print("=========================================================================")
    print("=== NYAYA LEGAL OS — PRODUCTION API VERIFICATION TEST                 ===")
    print("=========================================================================")

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[+] Health check response:", res.json())

    # 2. Test query 1: Section conversion
    q1 = {"query": "Convert legacy IPC Section 302 to Bharatiya Nyaya Sanhita, 2023 equivalent."}
    res1 = client.post("/api/v1/query", json=q1)
    assert res1.status_code == 200, f"Query 1 failed: {res1.text}"
    ans1 = res1.json()
    print("\n[+] Query 1 Answer:", ans1["answer"])
    print("    Grounding Status:", ans1["grounding_status"])
    print("    Latency:", ans1["latency_ms"], "ms")

    # 3. Test query 2: Procedural timeline
    q2 = {"query": "What is the statutory timeline for pronouncement of judgment after conclusion of trial under BNSS Section 392?"}
    res2 = client.post("/api/v1/query", json=q2)
    assert res2.status_code == 200, f"Query 2 failed: {res2.text}"
    ans2 = res2.json()
    print("\n[+] Query 2 Answer:", ans2["answer"])
    print("    Grounding Status:", ans2["grounding_status"])
    print("    Latency:", ans2["latency_ms"], "ms")

    # 4. Test query 3: Adversarial Trap
    q3 = {"query": "Did the Bharatiya Nyaya Sanhita, 2023 repeal and replace the Code of Criminal Procedure, 1973?"}
    res3 = client.post("/api/v1/query", json=q3)
    assert res3.status_code == 200, f"Query 3 failed: {res3.text}"
    ans3 = res3.json()
    print("\n[+] Query 3 (Adversarial Trap) Answer:", ans3["answer"])
    print("    Grounding Status:", ans3["grounding_status"])
    print("    Latency:", ans3["latency_ms"], "ms")

    print("\n=========================================================================")
    print("=== PRODUCTION API TEST PASSED (ALL ENDPOINTS VERIFIED)               ===")
    print("=========================================================================")

if __name__ == "__main__":
    test_api()
