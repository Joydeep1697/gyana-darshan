"""issue_planner.py — Nyaya Legal OS Legal Issue Planner & Candidate Budget Allocator (Phase 8.2J).

Constructs an Issue Plan from structured legal issues and dynamically allocates candidate budgets:
- Distinguishes PRIMARY, SECONDARY, and TERTIARY legal issues.
- Calculates per-issue candidate budgets for final evidence pack (top_k).
- Allocates internal candidate pool size (e.g. 15-20 per issue) for broad internal discovery.
- Guarantees evidence coverage across every active legal regime without single-issue crowding.
"""

from typing import Dict, List, Any, Set, Tuple

class LegalIssuePlanner:
    def __init__(self, default_top_k: int = 10):
        self.default_top_k = default_top_k

    def create_issue_plan(self, issue_analysis: Dict[str, Any], top_k: int = None) -> Dict[str, Any]:
        k = top_k or self.default_top_k
        primary_issues = issue_analysis.get("primary_issues", [])
        secondary_issues = issue_analysis.get("secondary_issues", [])
        active_statutes = issue_analysis.get("active_statutes", [])

        all_detected_issues = []
        issue_counter = 1

        # 1. Primary Issues (Substantive Offences, Core Child Protection)
        for p in primary_issues:
            all_detected_issues.append({
                "issue_id": f"I{issue_counter}",
                "priority": "PRIMARY",
                "domain": p.get("domain", "substantive"),
                "statute": p.get("statute", "BNS"),
                "concept": p.get("concept", "general"),
                "target_sections": p.get("target_sections", []),
                "fact_triggers": p.get("fact_triggers", []),
                "internal_pool_size": 20
            })
            issue_counter += 1

        # 2. Secondary Issues (Procedural Safeguards, Electronic Evidence, Mandatory Reporting)
        for s in secondary_issues:
            # Avoid duplicate domain/concept/statute combos
            if any(i["statute"] == s.get("statute") and i["concept"] == s.get("concept") for i in all_detected_issues):
                continue
            all_detected_issues.append({
                "issue_id": f"I{issue_counter}",
                "priority": "SECONDARY",
                "domain": s.get("domain", "procedure_or_evidence"),
                "statute": s.get("statute", "BNSS"),
                "concept": s.get("concept", "general"),
                "target_sections": s.get("target_sections", []),
                "fact_triggers": s.get("fact_triggers", []),
                "internal_pool_size": 15
            })
            issue_counter += 1

        # If no issues were extracted, fallback to single general issue per active statute
        if not all_detected_issues:
            for st in (active_statutes or ["BNS"]):
                all_detected_issues.append({
                    "issue_id": f"I{issue_counter}",
                    "priority": "PRIMARY",
                    "domain": "general",
                    "statute": st,
                    "concept": "general_retrieval",
                    "target_sections": [],
                    "fact_triggers": [],
                    "internal_pool_size": 20
                })
                issue_counter += 1

        num_issues = len(all_detected_issues)

        # 3. Dynamic Candidate Budget Allocation for Final Evidence Set (summing to k)
        if num_issues == 1:
            all_detected_issues[0]["candidate_budget"] = k
        elif num_issues == 2:
            # 6 for primary, 4 for secondary (or 5 each if equal)
            if all_detected_issues[0]["priority"] == all_detected_issues[1]["priority"]:
                all_detected_issues[0]["candidate_budget"] = k // 2
                all_detected_issues[1]["candidate_budget"] = k - (k // 2)
            else:
                all_detected_issues[0]["candidate_budget"] = max(4, int(k * 0.6))
                all_detected_issues[1]["candidate_budget"] = k - all_detected_issues[0]["candidate_budget"]
        elif num_issues == 3:
            # e.g., 4 / 3 / 3 for k=10
            all_detected_issues[0]["candidate_budget"] = 4
            all_detected_issues[1]["candidate_budget"] = 3
            all_detected_issues[2]["candidate_budget"] = 3
        elif num_issues == 4:
            # e.g., 3 / 3 / 2 / 2 for k=10
            all_detected_issues[0]["candidate_budget"] = 3
            all_detected_issues[1]["candidate_budget"] = 3
            all_detected_issues[2]["candidate_budget"] = 2
            all_detected_issues[3]["candidate_budget"] = 2
        else:
            # 5+ issues: allocate at least 2 to primary, 1-2 to others
            remaining = k
            for idx, iss in enumerate(all_detected_issues):
                if idx == 0:
                    b = max(2, k // num_issues + 1)
                else:
                    b = max(1, remaining // (num_issues - idx))
                iss["candidate_budget"] = b
                remaining -= b

        return {
            "num_issues": num_issues,
            "is_multi_issue": num_issues > 1,
            "target_top_k": k,
            "issues": all_detected_issues
        }
