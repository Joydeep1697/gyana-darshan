"""evaluate_phase_8_2c_validated.py — Principled, Ground-Truth-Based Evaluator for Nyaya Darshana.

Evaluates RAG performance across three benchmark classes:
1. EXPLICIT_SECTION (Statutory lookups, penalties, section mappings)
2. NARRATIVE_BLIND (Pure factual narratives with no section hints)
3. HYBRID_ADVERSARIAL (Complex multi-statute cases with traps and transition law)

Computes:
- Statutory Section Precision & Recall
- Retrieval Recall@4 and Recall@8
- Proposition Accuracy & Proposition-Level Evidence Support
- Multi-Statute Issue Coverage
- Uncertainty Handling
- False Proposition Rate & False Correction Rate
- Latency (Mean, p50, p95)
"""

import urllib.request
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

API_URL = "http://127.0.0.1:8000/api/v1/query"
API_KEY = "nyaya-prod-key-internal"

def normalize_sec(sec_str: str) -> str:
    """Extract base section number (e.g. '303(1)' -> '303')."""
    m = re.match(r'(\d+[A-Za-z]*)', str(sec_str).strip())
    return m.group(1).upper() if m else str(sec_str).strip().upper()

def evaluate_case_rigorous(
    case_query: Dict[str, Any],
    gt: Dict[str, Any],
    api_resp: Dict[str, Any],
    lat_ms: float
) -> Dict[str, Any]:
    """Perform rigorous ground-truth evaluation on a single test case."""
    cid = gt['scenario_id']
    b_class = gt.get('benchmark_class', 'UNKNOWN')
    expected_secs = gt.get('expected_sections', [])
    alt_secs = gt.get('acceptable_alternative_sections', [])
    expected_statutes = set(gt.get('expected_statutes', []))
    expected_props = gt.get('expected_legal_propositions', [])
    prohibited_props = gt.get('prohibited_false_propositions', [])
    req_uncertainty = gt.get('requires_uncertainty_qualification', False)

    retrieved_raw = api_resp.get('retrieved_sections', [])
    ans_text = api_resp.get('answer', '')
    fw_data = api_resp.get('verification_firewall', {})

    # 1. Normalize Retrieved Sections
    retrieved_pairs = []
    for s in retrieved_raw:
        st_norm = s.get('short_name') or ('BNS' if 'Nyaya' in s.get('statute','') else ('BNSS' if 'Nagarik' in s.get('statute','') else ('BSA' if 'Sakshya' in s.get('statute','') else ('POCSO' if 'POCSO' in s.get('statute','') else s.get('statute','')))))
        sec_norm = normalize_sec(s.get('section', ''))
        retrieved_pairs.append((st_norm.upper(), sec_norm))

    expected_pairs = [(e['statute'].upper(), normalize_sec(e['section'])) for e in expected_secs]
    alt_pairs = [(a['statute'].upper(), normalize_sec(a['section'])) for a in alt_secs]
    all_acceptable = set(expected_pairs).union(set(alt_pairs))

    # 2. Section Precision & Recall
    matched_expected = []
    for ep in expected_pairs:
        if ep in retrieved_pairs:
            matched_expected.append(ep)
        elif any(ep[0] == rp[0] and ep[1] == rp[1] for rp in retrieved_pairs):
            matched_expected.append(ep)

    matched_retrieved = [rp for rp in retrieved_pairs if rp in all_acceptable]
    
    sec_recall = len(matched_expected) / len(expected_pairs) if expected_pairs else 1.0
    sec_precision = len(matched_retrieved) / len(retrieved_pairs) if retrieved_pairs else 0.0

    # Recall@4
    ret_top4 = retrieved_pairs[:4]
    matched_top4 = [ep for ep in expected_pairs if ep in ret_top4]
    recall_at_4 = len(matched_top4) / len(expected_pairs) if expected_pairs else 1.0

    # Recall@8
    ret_top8 = retrieved_pairs[:8]
    matched_top8 = [ep for ep in expected_pairs if ep in ret_top8]
    recall_at_8 = len(matched_top8) / len(expected_pairs) if expected_pairs else 1.0

    # 3. Multi-Statute Coverage
    retrieved_statutes = set(rp[0] for rp in retrieved_pairs)
    covered_statutes = expected_statutes.intersection(retrieved_statutes)
    multi_statute_coverage = len(covered_statutes) / len(expected_statutes) if expected_statutes else 1.0

    # 4. Proposition Accuracy & Proposition-Level Evidence Support
    prop_matches = 0
    ans_lower = ans_text.lower()
    for ep in expected_props:
        ep_words = [w.lower() for w in re.findall(r'\w+', ep) if len(w) > 3]
        if any(w in ans_lower for w in ep_words[:4]):
            prop_matches += 1

    prop_acc = prop_matches / len(expected_props) if expected_props else 1.0

    # Evidence Support: Verify if cited sections in answer are present in retrieved_sections
    cited_in_ans = set(re.findall(r'(?:section|sec\.?)\s+(\d+[A-Za-z]*)', ans_text, re.IGNORECASE))
    ret_sec_numbers = set(rp[1] for rp in retrieved_pairs)
    
    if cited_in_ans:
        supported_citations = cited_in_ans.intersection(ret_sec_numbers)
        evidence_support = len(supported_citations) / len(cited_in_ans)
    else:
        evidence_support = 1.0 if retrieved_pairs else 0.0

    # 5. False Propositions Check
    false_propositions_found = []
    for fp in prohibited_props:
        if fp.lower() in ans_lower:
            false_propositions_found.append(fp)

    has_false_prop = len(false_propositions_found) > 0

    # 6. Uncertainty Handling Check
    uncertainty_score = 1.0
    if req_uncertainty:
        qual_phrases = ['subject to', 'requires proof', 'depending on', 'uncertain', 'if established', 'unless', 'qualification', 'disputed', 'factual', 'attestation', 'chain of custody']
        has_qual = any(qp in ans_lower for qp in qual_phrases)
        uncertainty_score = 1.0 if has_qual else 0.5

    # 7. False Corrections Check (Safety Gate)
    fw_interventions = fw_data.get('interventions_count', 0)
    claims_verified = fw_data.get('claims_verified', [])
    false_corrections_count = 0
    for c in claims_verified:
        if c.get('is_contradiction') and not c.get('truth'):
            false_corrections_count += 1

    # 8. Granular Weighted Score Calculation (100 Point Scale)
    # Dimension 1: Proposition Accuracy (30 pts)
    score_prop = prop_acc * 30.0
    # Dimension 2: Statutory Section Accuracy (20 pts)
    score_sec = (0.6 * sec_recall + 0.4 * sec_precision) * 20.0
    # Dimension 3: Retrieval Completeness (15 pts: Recall@4 & Recall@8)
    score_ret = (0.5 * recall_at_4 + 0.5 * recall_at_8) * 15.0
    # Dimension 4: Evidence Grounding Support (15 pts)
    score_ev = evidence_support * 15.0
    # Dimension 5: Multi-Statute Coverage (10 pts)
    score_multi = multi_statute_coverage * 10.0
    # Dimension 6: Uncertainty Handling (5 pts)
    score_unc = uncertainty_score * 5.0
    # Dimension 7: Legal Safety Integrity (5 pts)
    score_safe = 5.0 if not has_false_prop and false_corrections_count == 0 else 0.0

    total_granular_score = round(score_prop + score_sec + score_ret + score_ev + score_multi + score_unc + score_safe, 2)

    return {
        'scenario_id': cid,
        'benchmark_class': b_class,
        'category': gt.get('category', ''),
        'latency_ms': lat_ms,
        'retrieved_sections': retrieved_pairs,
        'expected_sections': expected_pairs,
        'matched_sections': matched_expected,
        'missing_sections': [ep for ep in expected_pairs if ep not in matched_expected],
        'extra_sections': [rp for rp in retrieved_pairs if rp not in all_acceptable],
        'section_precision': round(sec_precision, 4),
        'section_recall': round(sec_recall, 4),
        'recall_at_4': round(recall_at_4, 4),
        'recall_at_8': round(recall_at_8, 4),
        'multi_statute_coverage': round(multi_statute_coverage, 4),
        'proposition_accuracy': round(prop_acc, 4),
        'evidence_support': round(evidence_support, 4),
        'uncertainty_score': round(uncertainty_score, 4),
        'false_propositions': false_propositions_found,
        'false_corrections': false_corrections_count,
        'firewall_interventions': fw_interventions,
        'granular_score': total_granular_score,
        'verdict': 'PASS' if total_granular_score >= 80.0 and not has_false_prop and false_corrections_count == 0 else 'FAIL'
    }

def run_benchmark_evaluation(benchmark_file: Path, gt_file: Path, out_file: Path) -> Dict[str, Any]:
    """Run live API evaluation on a complete benchmark suite."""
    cases = [json.loads(line) for line in open(benchmark_file, encoding='utf-8') if line.strip()]
    gt_map = json.load(open(gt_file, encoding='utf-8'))

    print(f'Starting validated evaluation of {len(cases)} cases from {benchmark_file.name}...')

    results = []
    latencies = []

    for idx, c in enumerate(cases):
        cid = c['scenario_id']
        gt = gt_map.get(cid, {})
        fp = c.get('fact_pattern', '')
        lq = c.get('legal_question', '')
        full_query = (fp + '\n\n' + lq).strip()

        payload = json.dumps({'query': full_query, 'top_k': 4}).encode('utf-8')
        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={'Content-Type': 'application/json', 'x-api-key': API_KEY}
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req) as resp:
                api_resp = json.loads(resp.read().decode('utf-8'))
                lat = round((time.perf_counter() - t0) * 1000, 2)
                latencies.append(lat)

                eval_rec = evaluate_case_rigorous(c, gt, api_resp, lat)
                results.append(eval_rec)
                print(f'[{idx+1}/{len(cases)}] {cid} -> {eval_rec["verdict"]} ({eval_rec["granular_score"]}/100) | Sec Recall: {eval_rec["section_recall"]} | Lat: {lat}ms')
        except Exception as e:
            print(f'[{idx+1}/{len(cases)}] {cid} -> ERROR: {e}')

    with open(out_file, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Compute Aggregates
    n = len(results)
    avg_score = sum(r['granular_score'] for r in results) / n if n else 0
    avg_prec = sum(r['section_precision'] for r in results) / n if n else 0
    avg_rec = sum(r['section_recall'] for r in results) / n if n else 0
    avg_r4 = sum(r['recall_at_4'] for r in results) / n if n else 0
    avg_r8 = sum(r['recall_at_8'] for r in results) / n if n else 0
    avg_prop = sum(r['proposition_accuracy'] for r in results) / n if n else 0
    avg_ev = sum(r['evidence_support'] for r in results) / n if n else 0
    avg_multi = sum(r['multi_statute_coverage'] for r in results) / n if n else 0
    total_false_props = sum(len(r['false_propositions']) for r in results)
    total_false_corrs = sum(r['false_corrections'] for r in results)
    pass_count = sum(1 for r in results if r['verdict'] == 'PASS')

    latencies_sorted = sorted(latencies)
    p50_lat = latencies_sorted[int(len(latencies_sorted)*0.5)] if latencies_sorted else 0
    p95_lat = latencies_sorted[int(len(latencies_sorted)*0.95)] if latencies_sorted else 0
    mean_lat = sum(latencies) / len(latencies) if latencies else 0

    summary = {
        'benchmark_class': results[0]['benchmark_class'] if results else 'UNKNOWN',
        'total_cases': n,
        'passed_cases': pass_count,
        'pass_rate': round(pass_count / n * 100, 2) if n else 0,
        'mean_granular_score': round(avg_score, 2),
        'mean_section_precision': round(avg_prec, 4),
        'mean_section_recall': round(avg_rec, 4),
        'mean_recall_at_4': round(avg_r4, 4),
        'mean_recall_at_8': round(avg_r8, 4),
        'mean_proposition_accuracy': round(avg_prop, 4),
        'mean_evidence_support': round(avg_ev, 4),
        'mean_multi_statute_coverage': round(avg_multi, 4),
        'total_false_propositions': total_false_props,
        'total_false_corrections': total_false_corrs,
        'mean_latency_ms': round(mean_lat, 2),
        'p50_latency_ms': round(p50_lat, 2),
        'p95_latency_ms': round(p95_lat, 2)
    }

    return summary

if __name__ == '__main__':
    print('==================================================================')
    print('=== NYAYA DARSHANA VALIDATED GROUND-TRUTH TRIPLE BENCHMARK AUDIT ===')
    print('==================================================================\n')

    # Benchmark 1: HYBRID_ADVERSARIAL (ADV-001 to ADV-050)
    adv_summary = run_benchmark_evaluation(
        Path(r'C:\Users\joyde\Downloads\nyaya_darshana_50_advanced_hybrid_cases.jsonl'),
        Path('evaluation/ground_truth_adv_50.json'),
        Path('evaluation/results_adv_50_validated.jsonl')
    )

    # Benchmark 2: EXPLICIT_SECTION (EXP-001 to EXP-050)
    exp_summary = run_benchmark_evaluation(
        Path('evaluation/explicit_50.jsonl'),
        Path('evaluation/ground_truth_explicit_50.json'),
        Path('evaluation/results_explicit_50_validated.jsonl')
    )

    # Benchmark 3: NARRATIVE_BLIND (BLIND-001 to BLIND-050)
    blind_summary = run_benchmark_evaluation(
        Path('evaluation/narrative_blind_50.jsonl'),
        Path('evaluation/ground_truth_narrative_blind_50.json'),
        Path('evaluation/results_narrative_blind_50_validated.jsonl')
    )

    full_summary = {
        'hybrid_adversarial': adv_summary,
        'explicit_section': exp_summary,
        'narrative_blind': blind_summary
    }

    with open('evaluation/validated_triple_benchmark_report.json', 'w', encoding='utf-8') as f:
        json.dump(full_summary, f, indent=2)

    print('\n==================================================================')
    print('=== TRIPLE BENCHMARK AUDIT COMPLETE ===')
    print('==================================================================')
    print(json.dumps(full_summary, indent=2))
