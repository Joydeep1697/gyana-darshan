import json

with open("d:/Nova Legal/evaluation/phase_8_2b_novel_scenario_benchmark.jsonl", "r", encoding="utf-8") as f:
    bench = {r["scenario_id"]: r for r in [json.loads(l) for l in f if l.strip()]}

with open("d:/Nova Legal/evaluation/phase_8_2b_per_record_results.jsonl", "r", encoding="utf-8") as f:
    results = {r["scenario_id"]: r for r in [json.loads(l) for l in f if l.strip()]}

for sid in ["A05", "I07"]:
    print(f"\n--- {sid} ---")
    print("Benchmark Rec:", bench[sid])
    print("Result Rec:", results[sid])
