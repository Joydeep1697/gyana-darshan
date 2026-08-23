import sys
from pathlib import Path
sys.path.append(r"d:\Gyana Darshan")
import json
from evaluation.run_phase_8_2d_stress_benchmark import check_prohibited_claims

recs = [json.loads(l) for l in open("d:/Gyana Darshan/evaluation/phase_8_2d_per_record_results.jsonl", encoding="utf-8") if l.strip()]
bench = {x["scenario_id"]: x for x in [json.loads(l) for l in open("d:/Gyana Darshan/evaluation/phase_8_2d_stress_benchmark.jsonl", encoding="utf-8")]}

h1_recs = [r for r in recs if r["failure_code"] == "H1"]
print(f"Total H1 records: {len(h1_recs)}")

for r in h1_recs:
    b = bench[r["scenario_id"]]
    has_p, viols = check_prohibited_claims(r["final_answer"], b["prohibited_false_propositions"])
    print(f"[{r['scenario_id']}] Prohib: {b['prohibited_false_propositions']} | Viols: {viols}")
    print(f"   Final Ans Snippet: {repr(r['final_answer'][:150])}")
