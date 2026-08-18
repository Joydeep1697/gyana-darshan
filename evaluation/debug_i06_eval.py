import sys
from pathlib import Path
sys.path.append(r"d:\Nova Legal")
import json, re
from evaluation.run_phase_8_2b_novel_scenario_benchmark import evaluate_answer_correctness, check_prohibited_claims, extract_section_tokens

ans = "False. Under Indian Law, the procedural criminal statute is the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS), not 'BNS Criminal Procedure Code'."

recs = [json.loads(l) for l in open("d:/Nova Legal/evaluation/phase_8_2b_novel_scenario_benchmark.jsonl", encoding="utf-8") if l.strip()]
rec = [x for x in recs if x["scenario_id"] == "I06"][0]

print("Prohib check:", check_prohibited_claims(ans, rec["prohibited_false_propositions"]))
print("Expected statutes:", rec["expected_statutes"])
print("Expected sec:", rec["expected_sections"])
print("Expected prop:", rec["expected_legal_proposition"])
print("Tokens in ans:", extract_section_tokens(ans))
print("Final eval:", evaluate_answer_correctness(ans, rec["expected_statutes"], rec["expected_sections"], rec["expected_legal_proposition"], rec["prohibited_false_propositions"]))
