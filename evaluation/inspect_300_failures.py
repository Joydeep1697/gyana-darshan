import json

recs = [json.loads(l) for l in open("d:/Nova Legal/evaluation/phase_8_2d_per_record_results.jsonl", encoding="utf-8") if l.strip()]
failed = [r for r in recs if not r["final_pass"]]
print(f"Total Failed: {len(failed)}")

for f in failed:
    print(f"[{f['scenario_id']}] [{f['category']:25s}] Code: {f['failure_code']}")
    print(f"   Query: {f['query'][:120]}...")
    print(f"   Retrieved Sections: {f['retrieved_sections']}")
    print()
