import json

with open("d:/Nova Legal/evaluation/phase_8_2b_per_record_results.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(l) for l in f if l.strip()]

failed = [r for r in records if not r.get("final_pass")]
print(f"Total Failing Scenarios: {len(failed)}")

for r in failed:
    print(f"\n[{r['scenario_id']}] [{r['category']:<25}] {r['query']}")
    print(f"   Failure Code: {r.get('failure_code')}, Ret: {r.get('retrieval_verdict')}")
    print(f"   Final Answer Snippet: {r.get('final_answer')[:120]}")
