import json
adv_res = [json.loads(l) for l in open('evaluation/results_adv_50_validated.jsonl', encoding='utf-8') if l.strip()]
print("Keys in results_adv_50_validated:", adv_res[0].keys())
for r in adv_res:
    if r.get("scenario_id") in ["ADV-028", "ADV-033", "ADV-038"]:
        print(r.get("scenario_id"), r)
