"""run_test7.py — Executes Test 7 against Nyaya Darshan AI Chat engine.
"""

import sys
import json
import asyncio
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "Indian Legal"))

import openai
from app.config import get_llm_client_kwargs, LLM_MODEL
from app.routers.chat import LEGAL_SYSTEM_PROMPT
from app.legal_decision_tree import NyayaLegalDecisionEngine
from gyana_darshan_rag_nvidia import local_search
from app.config import INDEX_DIR

TEST_QUERY = "Since IPC Section 309 is still the general provision for attempting suicide, what punishment does it prescribe today? Do not assume my premise is correct. Verify whether IPC Section 309 is currently operative and identify the current legal position."

async def run_test7():
    print("=== RUNNING TEST 7 ===")
    print(f"QUERY: {TEST_QUERY}\n")
    
    # 1. Decision Analysis
    analysis = NyayaLegalDecisionEngine.analyze_query(TEST_QUERY)
    
    # 2. Local RAG Search
    search_results = await asyncio.to_thread(local_search, TEST_QUERY, INDEX_DIR)
    top_chunks = search_results[:4]
    
    context_parts = []
    for r in top_chunks:
        title = r.get('title', 'Legal Document')
        text = r.get('text', '').strip()
        context_parts.append(f"Document: {title}\nContent: {text}")
        
    context = "\n\n---\n\n".join(context_parts)
    if analysis.get("guidance"):
        context = f"STATUTORY ARCHITECTURE ANALYSIS:\n{analysis['guidance']}\n\n" + context
        
    client = openai.OpenAI(**get_llm_client_kwargs())
    
    def run_llm():
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
                {"role": "user", "content": f"Relevant Legal Context:\n{context}\n\nUser Question: {TEST_QUERY}"}
            ],
            temperature=0.05,
            max_tokens=600,
        )
        return response.choices[0].message.content

    answer = await asyncio.to_thread(run_llm)
    print("--- RAW ANSWER START ---")
    print(answer)
    print("--- RAW ANSWER END ---")

if __name__ == "__main__":
    asyncio.run(run_test7())
