import json
from pathlib import Path

adv_gt = json.load(open('evaluation/ground_truth_adv_50.json', encoding='utf-8'))
adv_res = {json.loads(l)['scenario_id']: json.loads(l) for l in open('evaluation/results_adv_50_validated.jsonl', encoding='utf-8') if l.strip()}

for cid in ["ADV-028", "ADV-033", "ADV-038", "ADV-039", "ADV-044", "ADV-048"]:
    gt = adv_gt.get(cid, {})
    raw = adv_res.get(cid, {})
    print(f"=== {cid} ===")
    print("Category:", gt.get("category"))
    print("Expected Statutes:", gt.get("expected_statutes"))
    print("Expected Sections:", gt.get("expected_sections"))
    print("Query:", raw.get("prompt") or raw.get("query"))
    print()
