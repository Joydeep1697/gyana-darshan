import json

with open("d:/Nova Legal/evaluation/phase_8_2b_per_record_results.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(l) for l in f if l.strip()]

false_corrs = [r for r in records if r["firewall_verdict"] == "FALSE_CORRECTION"]
print("=== FALSE CORRECTIONS (SAFETY GATE VIOLATIONS) ===")
for r in false_corrs:
    print(f"\nScenario ID: {r['scenario_id']} | Category: {r['category']}")
    print(f"Query: {r['query']}")
    print(f"Failure Code: {r['failure_code']}")
    print(f"Raw Answer Snippet: {r['raw_answer'][:120]}...")
    print(f"Final Answer: {r['final_answer']}")

failed_records = [r for r in records if not r["final_pass"]]
print(f"\n=== TOTAL FAILURES: {len(failed_records)} / 125 ===")
by_code = {}
for r in failed_records:
    c = r["failure_code"]
    by_code.setdefault(c, []).append(r["scenario_id"])

for code, ids in by_code.items():
    print(f"{code} ({len(ids)}): {', '.join(ids[:15])}{'...' if len(ids)>15 else ''}")
