# legal_reranker.py — Multi-Factor Explainable Legal Reranker (Phase 8.2G Hardened)
#
# Objective:
# Score and rerank statutory candidate sections produced by parallel statute branches
# using transparent, multi-dimensional legal relevance factors, ensuring multi-statute balance.

import re
from typing import Dict, List, Any, Set, Tuple

class LegalReranker:
    """Multi-factor legal candidate reranker with explicit factor explanations."""

    def __init__(self):
        pass

    def rerank_candidates(self, query: str, candidates: List[Dict[str, Any]], issues: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        """Rerank candidates and provide factor-level explanations with branch balance."""
        scored_candidates = []
        q_lower = query.lower()
        q_tokens = set(re.findall(r'\b\w+\b', q_lower))

        active_statute_weights = {}
        for iss in issues:
            for st in iss.get("statute_candidates", []):
                active_statute_weights[st] = active_statute_weights.get(st, 0.0) + iss.get("weight", 1.0)

        for cand in candidates:
            st = cand.get("statute", "").upper()
            sec = str(cand.get("section", "")).strip()
            heading = cand.get("heading", "") or ""
            text = cand.get("text", "") or ""
            branch_score = cand.get("branch_score", 0.0)
            is_deterministic = cand.get("is_deterministic", False)

            total_score = 0.0
            ranking_factors = []

            # Factor 1: Branch base score & Deterministic Injection
            if is_deterministic:
                total_score += 100.0
                ranking_factors.append("Authoritative Deterministic Registry Hit: +100.0")
            else:
                total_score += branch_score * 0.6
                ranking_factors.append(f"Branch Retrieval Base Score: {branch_score * 0.6:.1f}")

            # Factor 2: Statute issue weight alignment
            st_weight = active_statute_weights.get(st, 1.0)
            st_bonus = min(35.0, st_weight * 10.0)
            total_score += st_bonus
            ranking_factors.append(f"Statute Issue Alignment ({st}): +{st_bonus:.1f}")

            # Factor 3: Heading Semantic Specificity
            heading_lower = heading.lower()
            heading_hits = [w for w in q_tokens if len(w) > 3 and w in heading_lower]
            if heading_hits:
                head_score = min(50.0, len(heading_hits) * 12.0)
                total_score += head_score
                ranking_factors.append(f"Heading Direct Hits ({len(heading_hits)}): +{head_score:.1f}")

            # Factor 4: Substantive Offence Priority
            if "offence" in q_lower or "liability" in q_lower or "punishment" in q_lower or "substantive" in q_lower:
                if st in ["BNS", "POCSO"] and sec not in ["1", "2", "3", "2(1)(d)", "42"]:
                    total_score += 20.0
                    ranking_factors.append("Substantive Offence Specificity Bonus: +20.0")

            # Factor 5: Evidence Admissibility Focus
            if "evidence" in q_lower or "prove" in q_lower or "admissibility" in q_lower or "record" in q_lower:
                if st == "BSA":
                    total_score += 25.0
                    ranking_factors.append("Evidence Admissibility Focus Bonus (BSA): +25.0")

            # Factor 6: Procedural Focus
            if "custody" in q_lower or "remand" in q_lower or "arrest" in q_lower or "bail" in q_lower or "procedure" in q_lower:
                if st == "BNSS":
                    total_score += 25.0
                    ranking_factors.append("Procedural Safeguard Focus Bonus (BNSS): +25.0")

            scored_candidates.append({
                "statute": st,
                "section": sec,
                "heading": heading,
                "text": text[:300],
                "score": round(total_score, 2),
                "ranking_factors": ranking_factors
            })

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        # Multi-Statute Diversified Selection (Guarantee top candidates from each active statute branch)
        statute_buckets = {}
        for c in scored_candidates:
            st = c["statute"]
            if st not in statute_buckets:
                statute_buckets[st] = []
            statute_buckets[st].append(c)

        diversified_results = []
        seen_secs = set()

        # Pass 1: Top 2 from each active statute bucket
        for st, cands in statute_buckets.items():
            for c in cands[:2]:
                key = (c["statute"], str(c["section"]).strip().upper())
                if key not in seen_secs:
                    diversified_results.append(c)
                    seen_secs.add(key)

        # Pass 2: Fill remaining up to top_k by global score
        for c in scored_candidates:
            if len(diversified_results) >= top_k:
                break
            key = (c["statute"], str(c["section"]).strip().upper())
            if key not in seen_secs:
                diversified_results.append(c)
                seen_secs.add(key)

        # Re-sort diversified results by score
        diversified_results.sort(key=lambda x: x["score"], reverse=True)

        results = []
        for rank_idx, item in enumerate(diversified_results[:top_k]):
            item_copy = dict(item)
            item_copy["rank"] = rank_idx + 1
            results.append(item_copy)

        return results
