# statute_aware_preserver.py — Statute-Aware Candidate Preservation Engine (Phase 8.3A)
#
# Objective:
# Prevent high-quality candidate sections from secondary legal statutes (e.g. BSA evidence,
# BNSS procedural safeguards) from being suppressed by dominant branches (e.g. BNS) during
# global reranking, while strictly preserving evidence sufficiency, zero false corrections,
# zero hallucinations, and sub-250ms latency.

import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set, Tuple, Optional
from retrieval.experimental_phase_8_3a.phase_8_3a_config import Phase83AConfig, get_config_c

@dataclass
class StatuteCandidate:
    statute: str
    section: str
    heading: str = ""
    text: str = ""
    retrieval_score: float = 0.0
    local_rank_score: float = 0.0
    global_rank_score: float = 0.0
    issue_relevance_score: float = 0.0
    concept_overlap_score: float = 0.0
    evidence_score: float = 0.0
    preservation_score: float = 0.0
    is_protected: bool = False
    is_deterministic: bool = False
    ranking_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statute": self.statute,
            "section": self.section,
            "heading": self.heading,
            "text": self.text[:300] if self.text else "",
            "retrieval_score": round(self.retrieval_score, 2),
            "local_rank_score": round(self.local_rank_score, 2),
            "global_rank_score": round(self.global_rank_score, 2),
            "issue_relevance_score": round(self.issue_relevance_score, 2),
            "concept_overlap_score": round(self.concept_overlap_score, 2),
            "evidence_score": round(self.evidence_score, 2),
            "preservation_score": round(self.preservation_score, 2),
            "score": round(self.global_rank_score, 2),
            "is_protected": self.is_protected,
            "is_deterministic": self.is_deterministic,
            "ranking_factors": self.ranking_factors
        }

class StatuteAwarePreserver:
    """Statute-Aware Candidate Preservation and Calibrated Global Fusion Engine."""

    def __init__(self, config: Optional[Phase83AConfig] = None):
        self.config = config or get_config_c()

    def set_config(self, config: Phase83AConfig):
        self.config = config

    def _normalize_section(self, sec_str: Any) -> str:
        s = str(sec_str).strip()
        m = re.match(r'(\d+[A-Za-z]*(?:\(\w+\))?)', s)
        return m.group(1).upper() if m else s.upper()

    def _compute_issue_relevance(self, statute: str, issues: List[Dict[str, Any]]) -> float:
        """Compute statute relevance weight across decomposed query issues."""
        if not issues:
            return 1.0 if statute == "BNS" else 0.0
        
        statute_upper = statute.upper()
        total_weight = 0.0
        matched_weight = 0.0

        for iss in issues:
            w = float(iss.get("weight", 1.0))
            total_weight += w
            cand_stats = [s.upper() for s in iss.get("statute_candidates", [])]
            if statute_upper in cand_stats:
                matched_weight += w

        return min(1.0, (matched_weight / total_weight)) if total_weight > 0 else 0.0

    def _compute_concept_overlap(self, query_words: Set[str], heading: str, text: str) -> float:
        """Calculate semantic and keyword overlap against candidate heading and text."""
        heading_lower = heading.lower()
        text_lower = text[:400].lower()
        
        heading_matches = sum(1 for w in query_words if len(w) > 3 and w in heading_lower)
        text_matches = sum(1 for w in query_words if len(w) > 3 and w in text_lower)
        
        score = min(1.0, (heading_matches * 0.35) + (text_matches * 0.08))
        return score

    def _compute_evidence_score(self, cand_dict: Dict[str, Any], query_words: Set[str], query_lower: str) -> Tuple[float, List[str]]:
        """Calculate evidentiary sufficiency and relevance strength for candidate."""
        score = 0.0
        factors = []
        is_det = cand_dict.get("is_deterministic", False)
        branch_score = cand_dict.get("branch_score", 0.0)
        heading = cand_dict.get("heading", "") or ""
        sec = str(cand_dict.get("section", "")).strip()
        st = cand_dict.get("statute", "").upper()

        if is_det:
            score += 100.0
            factors.append("Authoritative Deterministic Registry Hit: +100.0")
        else:
            score += branch_score * 0.5
            factors.append(f"Branch Base Evidence: {branch_score * 0.5:.1f}")

        # Check section number in query
        if sec in query_words and sec not in ["1", "2", "3"]:
            score += 35.0
            factors.append(f"Explicit Section Reference ({sec}): +35.0")

        # Heading keyword overlaps
        heading_lower = heading.lower()
        hits = [w for w in query_words if len(w) > 3 and w in heading_lower]
        if hits:
            h_score = min(40.0, len(hits) * 10.0)
            score += h_score
            factors.append(f"Heading Element Overlap ({len(hits)}): +{h_score:.1f}")

        # Domain specific bonus alignments
        if st in ["BNS", "POCSO"] and any(k in query_lower for k in ["offence", "liability", "punish", "substantive", "stole", "forged", "threat"]):
            if sec not in ["1", "2", "3", "2(1)(d)", "42"]:
                score += 15.0
                factors.append("Substantive Offence Alignment: +15.0")

        if st == "BSA" and any(k in query_lower for k in ["evidence", "prove", "admissib", "record", "electronic", "cctv", "certificate", "oral", "witness"]):
            score += 20.0
            factors.append("Evidence Admissibility Alignment: +20.0")

        if st == "BNSS" and any(k in query_lower for k in ["custody", "remand", "arrest", "bail", "procedure", "fir", "investigat", "search", "seizure", "undertrial"]):
            score += 20.0
            factors.append("Procedural Safeguard Alignment: +20.0")

        return score, factors

    def evaluate_candidates(
        self,
        query: str,
        branch_results: Dict[str, List[Dict[str, Any]]],
        issues: List[Dict[str, Any]],
        concept_expansion: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[StatuteCandidate]]:
        """Evaluate and convert raw branch candidate dictionaries to rich StatuteCandidate models."""
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        if concept_expansion:
            for eq in concept_expansion.get("expanded_retrieval_queries", []):
                query_words.update(re.findall(r'\b\w+\b', eq.lower()))

        evaluated_by_statute: Dict[str, List[StatuteCandidate]] = {}

        for statute, raw_cands in branch_results.items():
            evaluated_by_statute[statute] = []
            iss_rel = self._compute_issue_relevance(statute, issues)

            for cand_dict in raw_cands:
                retrieval_score = float(cand_dict.get("branch_score", 0.0))
                is_det = cand_dict.get("is_deterministic", False)
                if retrieval_score <= 0.0 and not is_det:
                    continue

                ev_score, factors = self._compute_evidence_score(cand_dict, query_words, query_lower)
                overlap = self._compute_concept_overlap(query_words, cand_dict.get("heading", ""), cand_dict.get("text", ""))

                # Local rank score
                local_rank_score = (100.0 if is_det else retrieval_score)

                # Global rank score
                global_rank_score = ev_score + (iss_rel * 25.0) + (overlap * 20.0)

                # Preservation score (calibrated composite)
                preservation_score = (
                    (100.0 if is_det else local_rank_score * 0.3) +
                    (iss_rel * 30.0) +
                    (overlap * 25.0) +
                    (ev_score * 0.4)
                )

                candidate = StatuteCandidate(
                    statute=statute,
                    section=str(cand_dict.get("section", "")).strip(),
                    heading=cand_dict.get("heading", "") or "",
                    text=cand_dict.get("text", "") or "",
                    retrieval_score=retrieval_score,
                    local_rank_score=local_rank_score,
                    global_rank_score=global_rank_score,
                    issue_relevance_score=iss_rel,
                    concept_overlap_score=overlap,
                    evidence_score=ev_score,
                    preservation_score=preservation_score,
                    is_protected=False,
                    is_deterministic=is_det,
                    ranking_factors=factors
                )
                evaluated_by_statute[statute].append(candidate)

            # Sort within branch by local_rank_score descending, deterministic first
            evaluated_by_statute[statute].sort(
                key=lambda c: (1 if c.is_deterministic else 0, c.local_rank_score, c.evidence_score),
                reverse=True
            )

        return evaluated_by_statute

    def preserve_and_fuse(
        self,
        query: str,
        branch_results: Dict[str, List[Dict[str, Any]]],
        issues: List[Dict[str, Any]],
        concept_expansion: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Execute candidate preservation and calibrated global fusion."""
        top_k = top_k or self.config.top_k_final
        evaluated_by_statute = self.evaluate_candidates(query, branch_results, issues, concept_expansion)

        mode = self.config.mode
        protected_candidates: List[StatuteCandidate] = []
        all_candidates: List[StatuteCandidate] = []

        for st, cands in evaluated_by_statute.items():
            all_candidates.extend(cands)

        # -------------------------------------------------------------
        # CONFIGURATION A: Phase 8.2G Baseline Behavior (No Preservation)
        # -------------------------------------------------------------
        if mode == "CONFIG_A":
            # Global score sorting with simple multi-statute pass-1 / pass-2
            all_candidates.sort(key=lambda c: (c.global_rank_score, c.evidence_score), reverse=True)
            statute_buckets: Dict[str, List[StatuteCandidate]] = {}
            for c in all_candidates:
                if c.statute not in statute_buckets:
                    statute_buckets[c.statute] = []
                statute_buckets[c.statute].append(c)

            diversified: List[StatuteCandidate] = []
            seen = set()
            for st, cands in statute_buckets.items():
                for c in cands[:2]:
                    key = (c.statute, self._normalize_section(c.section))
                    if key not in seen:
                        diversified.append(c)
                        seen.add(key)

            for c in all_candidates:
                if len(diversified) >= top_k:
                    break
                key = (c.statute, self._normalize_section(c.section))
                if key not in seen:
                    diversified.append(c)
                    seen.add(key)

            diversified.sort(key=lambda c: c.global_rank_score, reverse=True)
            return self._finalize_results(diversified[:top_k])

        # -------------------------------------------------------------
        # CONFIGURATION B: Hard Active-Statute Preservation
        # -------------------------------------------------------------
        elif mode == "CONFIG_B":
            # Identify active statutes from issues and candidate presence
            active_statutes = set()
            for iss in issues:
                for st in iss.get("statute_candidates", []):
                    active_statutes.add(st.upper())

            for st, cands in evaluated_by_statute.items():
                if not cands:
                    continue
                # If statute is active or has positive retrieval score
                if st.upper() in active_statutes or (cands[0].retrieval_score > 0 and cands[0].evidence_score > 0):
                    top_cand = cands[0]
                    top_cand.is_protected = True
                    top_cand.ranking_factors.append("Config B Hard Active-Statute Protected")
                    protected_candidates.append(top_cand)
                    if len(protected_candidates) >= self.config.maximum_protected_candidates:
                        break

            # Fuse protected candidates with global candidates
            return self._fuse_protected_and_global(protected_candidates, all_candidates, top_k)

        # -------------------------------------------------------------
        # CONFIGURATION C: Calibrated Threshold-Gated Preservation
        # -------------------------------------------------------------
        elif mode == "CONFIG_C":
            # For each detected active statute branch, check preservation criteria
            active_statutes = set()
            for iss in issues:
                for st in iss.get("statute_candidates", []):
                    active_statutes.add(st.upper())

            for st, cands in evaluated_by_statute.items():
                if not cands:
                    continue
                st_upper = st.upper()
                top_cand = cands[0]

                # Qualification check:
                # 1. Deterministic hit is always preserved
                # 2. Candidate must satisfy minimum issue relevance & evidence & preservation thresholds
                is_eligible = False
                if top_cand.is_deterministic:
                    is_eligible = True
                elif (top_cand.issue_relevance_score >= self.config.minimum_issue_relevance and
                      top_cand.evidence_score >= self.config.minimum_evidence_score and
                      top_cand.preservation_score >= self.config.branch_preservation_threshold):
                    is_eligible = True

                # Demote non-substantive general definitions if not specifically queried
                sec_norm = self._normalize_section(top_cand.section)
                if sec_norm in ["1", "2", "3", "2(1)(D)", "42"] and not top_cand.is_deterministic:
                    if top_cand.evidence_score < 30.0:
                        is_eligible = False

                if is_eligible:
                    top_cand.is_protected = True
                    top_cand.ranking_factors.append(
                        f"Config C Evidence-Gated Preservation Protected (EvScore: {top_cand.evidence_score:.1f}, IssRel: {top_cand.issue_relevance_score:.2f})"
                    )
                    protected_candidates.append(top_cand)
                    if len(protected_candidates) >= self.config.maximum_protected_candidates:
                        break

            return self._fuse_protected_and_global(protected_candidates, all_candidates, top_k)

        # -------------------------------------------------------------
        # CONFIGURATION D: Preservation Multiplier / Global Bonus
        # -------------------------------------------------------------
        elif mode == "CONFIG_D":
            # Identify leading candidate per active statute and grant preservation bonus
            active_statutes = set()
            for iss in issues:
                for st in iss.get("statute_candidates", []):
                    active_statutes.add(st.upper())

            for st, cands in evaluated_by_statute.items():
                if not cands:
                    continue
                st_upper = st.upper()
                top_cand = cands[0]
                if (top_cand.is_deterministic or
                    (top_cand.issue_relevance_score >= self.config.minimum_issue_relevance and
                     top_cand.evidence_score >= self.config.minimum_evidence_score)):
                    
                    bonus = min(self.config.max_preservation_bonus, top_cand.preservation_score * self.config.preservation_bonus_multiplier)
                    top_cand.global_rank_score += bonus
                    top_cand.ranking_factors.append(f"Config D Statute Preservation Bonus: +{bonus:.1f}")

            # Re-sort all candidates by adjusted global score
            all_candidates.sort(
                key=lambda c: (1 if c.is_deterministic else 0, c.global_rank_score, c.evidence_score),
                reverse=True
            )

            # Deduplicate and return top_k
            unique_results: List[StatuteCandidate] = []
            seen = set()
            for c in all_candidates:
                key = (c.statute.upper(), self._normalize_section(c.section))
                if key not in seen:
                    unique_results.append(c)
                    seen.add(key)
                if len(unique_results) >= top_k:
                    break

            return self._finalize_results(unique_results)

        # Fallback to Config A behavior
        all_candidates.sort(key=lambda c: c.global_rank_score, reverse=True)
        return self._finalize_results(all_candidates[:top_k])

    def _fuse_protected_and_global(
        self,
        protected_candidates: List[StatuteCandidate],
        all_candidates: List[StatuteCandidate],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Calibrated global fusion ensuring protected candidates are represented in Top-5 window."""
        # Sort protected candidates by preservation score descending
        protected_candidates.sort(
            key=lambda c: (1 if c.is_deterministic else 0, c.preservation_score, c.global_rank_score),
            reverse=True
        )

        # Sort all remaining global candidates
        all_candidates.sort(
            key=lambda c: (1 if c.is_deterministic else 0, c.global_rank_score, c.evidence_score),
            reverse=True
        )

        fused: List[StatuteCandidate] = []
        seen = set()

        # Step 1: Insert highest-scoring global candidate (preserve Top-1 section precision)
        if all_candidates:
            top1_global = all_candidates[0]
            fused.append(top1_global)
            seen.add((top1_global.statute.upper(), self._normalize_section(top1_global.section)))

        # Step 2: Insert protected secondary-statute candidates
        for p in protected_candidates:
            key = (p.statute.upper(), self._normalize_section(p.section))
            if key not in seen:
                fused.append(p)
                seen.add(key)

        # Step 3: Fill remaining positions up to top_k with remaining global candidates
        for c in all_candidates:
            if len(fused) >= top_k:
                break
            key = (c.statute.upper(), self._normalize_section(c.section))
            if key not in seen:
                fused.append(c)
                seen.add(key)

        # Step 4: Calibrate final ordering:
        # Keep deterministic / highest scoring at Top 1.
        # Ensure protected candidates remain within the Top-5 window.
        fused_final = self._calibrate_final_order(fused, top_k)
        return self._finalize_results(fused_final)

    def _calibrate_final_order(self, candidates: List[StatuteCandidate], top_k: int) -> List[StatuteCandidate]:
        """Ensure ordering is strictly deterministic, respects Top-1 leader, and preserves secondary branch presence in Top-5."""
        if not candidates:
            return []

        # Deterministic items always lead
        det_items = [c for c in candidates if c.is_deterministic]
        non_det_items = [c for c in candidates if not c.is_deterministic]

        # In non-deterministic items:
        # Top-1 highest global score candidate stays ahead
        # Protected candidates are placed in Top-3 to Top-5 window if they possess high evidence
        if non_det_items:
            # Sort by composite ranking score: global_rank_score + (15.0 if is_protected else 0.0)
            non_det_items.sort(
                key=lambda c: (
                    c.global_rank_score + (15.0 if c.is_protected else 0.0),
                    c.evidence_score,
                    c.statute,
                    c.section
                ),
                reverse=True
            )

        ordered = det_items + non_det_items
        return ordered[:top_k]

    def _finalize_results(self, candidates: List[StatuteCandidate]) -> List[Dict[str, Any]]:
        """Format final list of candidate dictionaries with 1-based ranks."""
        results = []
        for idx, cand in enumerate(candidates):
            d = cand.to_dict()
            d["rank"] = idx + 1
            results.append(d)
        return results
