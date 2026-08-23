import json
data = json.load(open('evaluation/phase_8_2g_benchmark_results.json', encoding='utf-8'))
for r in data['per_case_results']:
    b_acc = r['baseline']['is_accurate']
    e_acc = r['experimental']['is_accurate']
    if b_acc != e_acc or not e_acc:
        b_rk = r['baseline']['best_rank']
        e_rk = r['experimental']['best_rank']
        print(f"{r['case_id']}: Base={b_acc} (rank {b_rk}), Exp={e_acc} (rank {e_rk}) | cat: {r['category']}")
