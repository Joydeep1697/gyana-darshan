import json

with open("d:/Nova Legal/evaluation/phase_8_2b_novel_scenario_benchmark.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(l) for l in f if l.strip()]

multi_records = [r for r in records if r["category"] == "MULTI_STATUTE"]
for r in multi_records:
    print(f"\nID: {r['scenario_id']}")
    print(f"Fact Pattern: {r['fact_pattern']}")
    print(f"Legal Question: {r['legal_question']}")
    print(f"Expected Statutes: {r['expected_statutes']}")
    print(f"Expected Sections: {r['expected_sections']}")
    print(f"Expected Prop: {r['expected_legal_proposition']}")
