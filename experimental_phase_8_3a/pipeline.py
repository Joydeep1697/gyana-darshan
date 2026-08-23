# pipeline.py — Phase 8.3A Experimental Retrieval & Candidate Preservation Pipeline
#
# Architecture (corrected):
#   Phase 8.2G LegalReranker scores are computed first and used as the authoritative
#   global_rank_score. The Statute-Aware Preserver then EXTENDS this output by pulling
#   displaced secondary-statute candidates back into the Top-5 window when they satisfy
#   configured evidence+relevance thresholds — without disturbing the Top-1 leader.

import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(r"d:\Gyana Darshan")
sys.path.append(str(BASE_DIR))

from retrieval.experimental.issue_decomposer import LegalIssueDecomposer
from retrieval.experimental.legal_concept_expander import LegalConceptExpander
from retrieval.experimental.parallel_statute_retriever import ParallelStatuteRetriever
from retrieval.experimental.legal_reranker import LegalReranker
from retrieval.experimental.evidence_sufficiency import EvidenceSufficiencyEvaluator
from retrieval.experimental_phase_8_3a.phase_8_3a_config import (
    Phase83AConfig, get_config_a, get_config_b, get_config_c, get_config_d
)


def _norm_sec(sec_str: Any) -> str:
    m = re.match(r'(\d+[A-Za-z]*)', str(sec_str).strip())
    return m.group(1).upper() if m else str(sec_str).strip().upper()


def _finalize(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for idx, c in enumerate(candidates):
        c2 = dict(c)
        c2["rank"] = idx + 1
        result.append(c2)
    return result


def _fuse(
    globally_ranked: List[Dict[str, Any]],
    protected_items: List[Dict[str, Any]],
    protected_keys: set,
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Merge protection-eligible secondary-statute candidates into globally ranked output.

    Guarantees:
    - Rank 1 is always the globally highest-scoring candidate (preserves Top-1 precision).
    - Protected candidates appear within Top-5 window.
    - Deduplication is enforced throughout.
    """
    fused: List[Dict[str, Any]] = []
    seen: set = set()

    # Pin globally highest-scoring candidate at Rank 1
    if globally_ranked:
        top1 = globally_ranked[0]
        k1 = (top1.get("statute", "").upper(), _norm_sec(top1.get("section", "")))
        fused.append(top1)
        seen.add(k1)
        protected_keys.discard(k1)

    # Insert protected secondary-statute candidates
    for p in sorted(protected_items, key=lambda x: x.get("score", 0.0), reverse=True):
        key = (p.get("statute", "").upper(), _norm_sec(p.get("section", "")))
        if key not in seen:
            fused.append(p)
            seen.add(key)

    # Fill remaining positions from globally ranked pool
    for c in globally_ranked:
        if len(fused) >= top_k:
            break
        key = (c.get("statute", "").upper(), _norm_sec(c.get("section", "")))
        if key not in seen:
            fused.append(c)
            seen.add(key)

    # Re-sort positions 2+ by global score (keep Rank 1 pinned)
    if len(fused) > 1:
        rest = sorted(fused[1:], key=lambda x: x.get("score", 0.0), reverse=True)
        fused = [fused[0]] + rest

    return _finalize(fused[:top_k])


class Phase83ALegalPipeline:
    """
    Phase 8.3A: Phase 8.2G LegalReranker (global scores) +
    Statute-Aware Preservation Fusion (secondary-branch protection).
    """

    def __init__(self, config: Optional[Phase83AConfig] = None):
        self.config = config or get_config_c()
        self.decomposer = LegalIssueDecomposer()
        self.expander = LegalConceptExpander()
        self.parallel_retriever = ParallelStatuteRetriever()
        self.reranker = LegalReranker()          # Phase 8.2G global scorer — unchanged
        self.sufficiency_evaluator = EvidenceSufficiencyEvaluator()

    def set_config(self, config: Phase83AConfig):
        self.config = config

    def process_query(
        self,
        query: str,
        per_statute_k: Optional[int] = None,
        top_k_final: Optional[int] = None
    ) -> Dict[str, Any]:
        per_statute_k = per_statute_k or self.config.per_statute_k
        top_k_final   = top_k_final   or self.config.top_k_final

        # Step 1-2: Issue Decomposition + Concept Expansion
        decomposition = self.decomposer.decompose_query(query)
        expansion     = self.expander.expand_query(query)

        # Step 3: Parallel Statute Retrieval
        parallel_results = self.parallel_retriever.retrieve_parallel_branches(
            query, per_statute_k=per_statute_k
        )
        branch_results = parallel_results["branch_results"]
        all_raw_cands  = parallel_results["candidates"]

        # Step 4a: Phase 8.2G global reranker — wide pool so preserver has material
        globally_ranked = self.reranker.rerank_candidates(
            query=query,
            candidates=all_raw_cands,
            issues=decomposition["issues"],
            top_k=top_k_final * 2
        )

        # Step 4b: Statute-Aware Candidate Preservation
        preserved_candidates = self._apply_preservation(
            query=query,
            globally_ranked=globally_ranked,
            branch_results=branch_results,
            issues=decomposition["issues"],
            top_k=top_k_final
        )

        # Step 5: Evidence Sufficiency
        sufficiency = self.sufficiency_evaluator.evaluate_sufficiency(
            issues=decomposition["issues"],
            reranked_evidence=preserved_candidates
        )

        evidence_pack      = self._format_evidence_pack(query, preserved_candidates, sufficiency)
        synthesized_answer = self._synthesize_grounded_answer(query, decomposition, preserved_candidates, sufficiency)

        return {
            "query": query,
            "config_mode": self.config.mode,
            "config_name": self.config.name,
            "decomposition": decomposition,
            "concept_expansion": expansion,
            "parallel_branches": branch_results,
            "retrieved_sections": preserved_candidates,
            "evidence_sufficiency": sufficiency,
            "evidence_pack": evidence_pack,
            "answer": synthesized_answer
        }

    # ------------------------------------------------------------------
    # Core preservation logic using Phase 8.2G global scores
    # ------------------------------------------------------------------

    def _issue_relevance(self, statute: str, issues: List[Dict[str, Any]]) -> float:
        if not issues:
            return 0.0
        total   = sum(float(i.get("weight", 1)) for i in issues)
        matched = sum(float(i.get("weight", 1)) for i in issues
                      if statute.upper() in [s.upper() for s in i.get("statute_candidates", [])])
        return min(1.0, matched / total) if total > 0 else 0.0

    def _evidence_score_for_cand(self, cand: Dict[str, Any], query: str, issues: List[Dict[str, Any]]) -> float:
        """Replicate LegalReranker factor scoring for a single candidate."""
        st       = cand.get("statute", "").upper()
        sec      = str(cand.get("section", "")).strip()
        heading  = (cand.get("heading") or "").lower()
        q_lower  = query.lower()
        q_tokens = set(re.findall(r'\b\w+\b', q_lower))
        bsc      = cand.get("branch_score", 0.0)
        is_det   = cand.get("is_deterministic", False)

        score = 100.0 if is_det else bsc * 0.6
        w     = self._issue_relevance(st, issues)
        score += min(35.0, w * 35.0)               # statute issue weight bonus (same cap as reranker)
        hits  = [t for t in q_tokens if len(t) > 3 and t in heading]
        score += min(50.0, len(hits) * 12.0)
        if st in ["BNS", "POCSO"] and sec not in ["1", "2", "3", "2(1)(d)", "42"]:
            if any(k in q_lower for k in ["offence", "punish", "theft", "forged", "robbery", "murder", "rape", "liability", "substantive"]):
                score += 20.0
        if st == "BSA" and any(k in q_lower for k in ["evidence", "admissib", "electronic", "record", "witness", "prove"]):
            score += 25.0
        if st == "BNSS" and any(k in q_lower for k in ["custody", "remand", "arrest", "bail", "procedure", "fir", "search", "seizure"]):
            score += 25.0
        return score

    def _best_per_statute(
        self,
        branch_results: Dict[str, List[Dict[str, Any]]],
        query: str,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        best: Dict[str, Dict[str, Any]] = {}
        for st, cands in branch_results.items():
            valid = [(c.get("branch_score", 0.0), c) for c in cands
                     if c.get("branch_score", 0.0) > 0 or c.get("is_deterministic")]
            if valid:
                valid.sort(key=lambda x: x[0], reverse=True)
                best[st.upper()] = valid[0][1]
        return best

    def _apply_preservation(
        self,
        query: str,
        globally_ranked: List[Dict[str, Any]],
        branch_results: Dict[str, List[Dict[str, Any]]],
        issues: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        mode = self.config.mode

        # CONFIG A: Pure Phase 8.2G pass-1/pass-2 diversification, no protection
        if mode == "CONFIG_A":
            return _finalize(globally_ranked[:top_k])

        best_per_statute = self._best_per_statute(branch_results, query, issues)

        # CONFIG B: Hard-protect top local candidate from every active statute
        if mode == "CONFIG_B":
            prot_items: List[Dict[str, Any]] = []
            prot_keys: set = set()
            for st, best_cand in best_per_statute.items():
                if best_cand.get("branch_score", 0.0) <= 0 and not best_cand.get("is_deterministic"):
                    continue
                p = dict(best_cand)
                p["statute"] = st
                p["score"]   = best_cand.get("branch_score", 0.0)
                p["is_protected"] = True
                key = (st, _norm_sec(best_cand.get("section", "")))
                prot_keys.add(key)
                prot_items.append(p)
                if len(prot_items) >= self.config.maximum_protected_candidates:
                    break
            return _fuse(globally_ranked, prot_items, prot_keys, top_k)

        # CONFIG C: Threshold-gated preservation
        if mode == "CONFIG_C":
            prot_items = []
            prot_keys  = set()
            min_rel  = self.config.minimum_issue_relevance
            min_ev   = self.config.minimum_evidence_score
            min_pres = self.config.branch_preservation_threshold
            max_prot = self.config.maximum_protected_candidates

            for st, best_cand in best_per_statute.items():
                iss_rel = self._issue_relevance(st, issues)
                ev_sc   = self._evidence_score_for_cand(best_cand, query, issues)
                is_det  = best_cand.get("is_deterministic", False)
                sec_n   = _norm_sec(best_cand.get("section", ""))

                # Reject generic definition/title sections unless deterministic
                if sec_n in ["1", "2", "3", "2(1)(D)", "42"] and not is_det and ev_sc < 30.0:
                    continue

                eligible = is_det or (iss_rel >= min_rel and ev_sc >= min_ev and ev_sc >= min_pres)
                if not eligible:
                    continue

                p = dict(best_cand)
                p["statute"] = st
                p["score"]   = ev_sc   # use ev score for sorting within protected items
                p["is_protected"] = True
                p["ranking_factors"] = p.get("ranking_factors", []) + [
                    f"Config C Protected (iss_rel={iss_rel:.2f}, ev={ev_sc:.1f})"
                ]
                key = (st, sec_n)
                prot_keys.add(key)
                prot_items.append(p)
                if len(prot_items) >= max_prot:
                    break

            return _fuse(globally_ranked, prot_items, prot_keys, top_k)

        # CONFIG D: Soft preservation bonus on top of global score
        if mode == "CONFIG_D":
            min_rel   = self.config.minimum_issue_relevance
            min_ev    = self.config.minimum_evidence_score
            bonus_mul = self.config.preservation_bonus_multiplier
            max_bonus = self.config.max_preservation_bonus

            augmented = []
            for c in globally_ranked:
                st      = c.get("statute", "").upper()
                iss_rel = self._issue_relevance(st, issues)
                ev_sc   = self._evidence_score_for_cand(best_per_statute.get(st, c), query, issues)
                c2 = dict(c)
                if iss_rel >= min_rel and ev_sc >= min_ev:
                    bonus = min(max_bonus, ev_sc * bonus_mul)
                    c2["score"] = c.get("score", 0.0) + bonus
                    c2["ranking_factors"] = c.get("ranking_factors", []) + [f"Config D Bonus +{bonus:.1f}"]
                augmented.append(c2)

            augmented.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            seen: set = set()
            deduped = []
            for c in augmented:
                key = (c.get("statute", "").upper(), _norm_sec(c.get("section", "")))
                if key not in seen:
                    deduped.append(c)
                    seen.add(key)
                if len(deduped) >= top_k:
                    break
            return _finalize(deduped)

        # Fallback
        return _finalize(globally_ranked[:top_k])

    # ------------------------------------------------------------------
    def _format_evidence_pack(self, query: str, candidates: List[Dict[str, Any]], sufficiency: Dict[str, Any]) -> str:
        lines = [
            f"=== EXPERIMENTAL PHASE 8.3A AUTHORITATIVE EVIDENCE PACK ===",
            f"Query: {query}",
            f"Configuration: {self.config.name}",
            f"Evidence Grounding Status: {sufficiency['overall_status']} (Sufficiency: {sufficiency['sufficiency_ratio']*100:.0f}%)",
            f"============================================================"
        ]
        for c in candidates:
            prot_tag = " [PROTECTED]" if c.get("is_protected") else ""
            lines.append(f"\n[Rank {c['rank']}{prot_tag}] {c['statute']} Section {c['section']}")
            if c.get("heading"):
                lines.append(f"Heading: {c['heading']}")
            score_val = c.get("score", 0.0)
            lines.append(f"Score: {score_val} (Factors: {', '.join(c.get('ranking_factors', [])[:2])})")
            lines.append(f"Text: {c.get('text', '')[:250]}...")
        return "\n".join(lines)

    def _synthesize_grounded_answer(self, query, decomposition, candidates, sufficiency) -> str:
        cit = ", ".join(f"{c['statute']} Section {c['section']}" for c in candidates[:4]) or "applicable provisions"
        issue_text = "; ".join(
            f"{i['issue_type']} (governed by {', '.join(i['statute_candidates'])})"
            for i in decomposition["issues"] if i["issue_type"] != "MULTI_STATUTE"
        )[:3 * 80] or "legal rights and liabilities"
        return (
            f"Based on authoritative statutory provisions grounded in the Official Gazette ({cit}), "
            f"the factual scenario discloses {issue_text}. "
            f"The legal determination is supported with an evidence sufficiency status of {sufficiency['overall_status']}. "
            f"Under the codified provisions, all statutory requirements and evidentiary procedural safeguards must be strictly satisfied."
        )
