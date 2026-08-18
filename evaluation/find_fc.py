import json

with open("d:/Nova Legal/evaluation/phase_8_2b_per_record_results.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(l) for l in f if l.strip()]

false_corrs = [r for r in records if r["firewall_verdict"] == "FALSE_CORRECTION"]
print(f"Total False Corrections: {len(false_corrs)}")
for r in false_corrs:
    print(f"\nScenario ID: {r['scenario_id']} | Category: {r['category']}")
    print(f"Query: {r['query']}")
    print(f"Failure Code: {r['failure_code']}")
    print(f"Raw Answer Snippet: {r['raw_answer'][:100]}")
    print(f"Final Answer: {r['final_answer']}")
