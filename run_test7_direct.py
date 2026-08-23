"""run_test7_direct.py — Fast direct execution of Test 7 using Nyaya Legal Decision Engine.
"""

import sys
import json
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

import openai
from app.config import get_llm_client_kwargs, LLM_MODEL
from app.routers.chat import LEGAL_SYSTEM_PROMPT
from app.legal_decision_tree import NyayaLegalDecisionEngine

TEST_QUERY = "Since IPC Section 309 is still the general provision for attempting suicide, what punishment does it prescribe today? Do not assume my premise is correct. Verify whether IPC Section 309 is currently operative and identify the current legal position."

def main():
    print("=== RUNNING TEST 7 DIRECT ===")
    
    analysis = NyayaLegalDecisionEngine.analyze_query(TEST_QUERY)
    
    client = openai.OpenAI(**get_llm_client_kwargs())
    
    prompt_context = f"""STATUTORY ARCHITECTURE ANALYSIS:
{analysis['guidance']}

STATUTORY BARE ACT CONTEXT:
- Indian Penal Code, 1860 (IPC) Section 309: Attempt to commit suicide (REPEALED & OMITTED).
- Bharatiya Nyaya Sanhita, 2023 (BNS): Section 309 IPC omitted; BNS Section 226 penalizes attempting suicide ONLY to compel or restrain a public servant.
- Mental Healthcare Act, 2017: Section 115 presumes severe stress for any person attempting suicide and prohibits trial, prosecution, or punishment under IPC.
- Statutory Repeal & Savings: BNS Section 358(1) repeals IPC.
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
            {"role": "user", "content": f"Relevant Legal Context:\n{prompt_context}\n\nUser Question: {TEST_QUERY}"}
        ],
        temperature=0.05,
        max_tokens=600,
    )

    answer = response.choices[0].message.content
    print("--- RAW ANSWER START ---")
    print(answer)
    print("--- RAW ANSWER END ---")

if __name__ == "__main__":
    main()
