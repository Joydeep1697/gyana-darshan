"""evidence_budget_engine.py — Nyaya Legal OS Evidence Budget & Legal Issue Coverage Engine (Phase 8.2L).

Eliminates cross-statute evidence crowding and guarantees multi-issue statutory representation:
1. Decomposes queries into active legal issues (Substantive, Procedural, Evidentiary, Special Statute).
2. Allocates strict per-issue candidate budgets within top_k (e.g. 4/3/3 for 3 issues, 3/3/2/2 for 4 issues).
3. Constructs independent per-issue priority queues (verified targets + reranked corpus candidates).
4. Executes fair round-robin multi-issue interleaving constrained by per-issue budgets.
"""

from typing import Dict, List, Any, Set, Tuple

class EvidenceBudgetEngine:
    def __init__(self, default_top_k: int = 10):
        self.default_top_k = default_top_k

    def allocate_issue_budgets(self, issues: List[Dict[str, Any]], top_k: int = 10) -> Dict[str, int]:
        num_issues = len(issues)
        budgets: Dict[str, int] = {}
        
        if num_issues == 0:
            return budgets
        
        if num_issues == 1:
            budgets[issues[0]["issue_id"]] = top_k
            return budgets

        if num_issues == 2:
            # 5 / 5 for equal, or 6 / 4 for primary / secondary
            p0 = issues[0].get("priority", "PRIMARY")
            p1 = issues[1].get("priority", "PRIMARY")
            if p0 == p1:
                b0 = top_k // 2
                budgets[issues[0]["issue_id"]] = b0
                budgets[issues[1]["issue_id"]] = top_k - b0
            else:
                budgets[issues[0]["issue_id"]] = 6
                budgets[issues[1]["issue_id"]] = 4
            return budgets

        if num_issues == 3:
            # 4 / 3 / 3
            budgets[issues[0]["issue_id"]] = 4
            budgets[issues[1]["issue_id"]] = 3
            budgets[issues[2]["issue_id"]] = 3
            return budgets

        if num_issues == 4:
            # 3 / 3 / 2 / 2
            budgets[issues[0]["issue_id"]] = 3
            budgets[issues[1]["issue_id"]] = 3
            budgets[issues[2]["issue_id"]] = 2
            budgets[issues[3]["issue_id"]] = 2
            return budgets

        # 5+ issues: allocate at least 2 to primary, 1-2 to others summing to top_k
        remaining = top_k
        for idx, iss in enumerate(issues):
            if idx == 0:
                b = max(2, top_k // num_issues + 1)
            else:
                b = max(1, remaining // (num_issues - idx))
            b = min(b, remaining)
            budgets[iss["issue_id"]] = b
            remaining -= b
        return budgets

    def select_diversified_evidence(
        self,
        issue_queues: Dict[str, List[Dict[str, Any]]],
        issue_budgets: Dict[str, int],
        top_k: int = 10,
        negative_distractors: Set[Tuple[str, str]] = None
    ) -> List[Dict[str, Any]]:
        negative_distractors = negative_distractors or set()
        selected: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        seen_sections: Set[Tuple[str, str]] = set()

        issue_ids = list(issue_queues.keys())
        if not issue_ids:
            return selected

        # Per-issue counts taken so far
        taken_counts = {iss_id: 0 for iss_id in issue_ids}

        # Round-robin selection constrained by issue budgets
        max_depth = max((len(q) for q in issue_queues.values()), default=0)

        for depth in range(max_depth):
            for iss_id in issue_ids:
                if len(selected) >= top_k:
                    break
                budget = issue_budgets.get(iss_id, 3)
                if taken_counts[iss_id] >= budget:
                    continue
                q = issue_queues.get(iss_id, [])
                if depth < len(q):
                    item = q[depth]
                    st = item.get("short_name") or ("BNS" if "Nyaya" in item.get("statute","") else ("BNSS" if "Nagarik" in item.get("statute","") else ("BSA" if "Sakshya" in item.get("statute","") else ("POCSO" if "POCSO" in item.get("statute","") else ""))))
                    sec_clean = str(item.get("section", "")).strip().upper()
                    sec_key = (st.upper(), sec_clean)

                    if sec_key in negative_distractors:
                        continue
                    if sec_key not in seen_sections and item["id"] not in seen_ids:
                        seen_sections.add(sec_key)
                        seen_ids.add(item["id"])
                        selected.append(item)
                        taken_counts[iss_id] += 1

            if len(selected) >= top_k:
                break

        # If slots remain (due to short queues), fill from any remaining candidates
        if len(selected) < top_k:
            for depth in range(max_depth):
                for iss_id in issue_ids:
                    if len(selected) >= top_k:
                        break
                    q = issue_queues.get(iss_id, [])
                    if depth < len(q):
                        item = q[depth]
                        st = item.get("short_name") or ("BNS" if "Nyaya" in item.get("statute","") else ("BNSS" if "Nagarik" in item.get("statute","") else ("BSA" if "Sakshya" in item.get("statute","") else ("POCSO" if "POCSO" in item.get("statute","") else ""))))
                        sec_clean = str(item.get("section", "")).strip().upper()
                        sec_key = (st.upper(), sec_clean)

                        if sec_key in negative_distractors:
                            continue
                        if sec_key not in seen_sections and item["id"] not in seen_ids:
                            seen_sections.add(sec_key)
                            seen_ids.add(item["id"])
                            selected.append(item)

        return selected[:top_k]
