"""legal_reranker.py — Nyaya Legal OS Multi-Signal Legal Reranker (Phase 8.2I).

Reranks candidate statutory sections using structured legal issue alignment:
FINAL_SCORE =
    w_lexical * lexical_score
  + w_statute * statute_scope_score
  + w_concept * concept_score
  + w_heading * heading_score
  + w_fact    * fact_alignment_score
  + w_branch  * issue_branch_score
  + w_subsec  * subsection_score
  - w_distract * distractor_penalty
"""

import re
from typing import Dict, List, Any, Set, Tuple

class LegalReranker:
    def __init__(
        self,
        w_lexical: float = 1.0,
        w_statute: float = 10.0,
        w_concept: float = 35.0,
        w_heading: float = 25.0,
        w_fact: float = 20.0,
        w_branch: float = 15.0,
        w_subsec: float = 10.0,
        w_distract: float = 40.0
    ):
        self.w_lexical = w_lexical
        self.w_statute = w_statute
        self.w_concept = w_concept
        self.w_heading = w_heading
        self.w_fact = w_fact
        self.w_branch = w_branch
        self.w_subsec = w_subsec
        self.w_distract = w_distract

    def score_candidate(
        self,
        rec: Dict[str, Any],
        query: str,
        query_words: Set[str],
        issue_analysis: Dict[str, Any]
    ) -> float:
        st_short = rec.get("short_name") or ("BNS" if "Nyaya" in rec.get("statute","") else ("BNSS" if "Nagarik" in rec.get("statute","") else ("BSA" if "Sakshya" in rec.get("statute","") else ("POCSO" if "POCSO" in rec.get("statute","") else ""))))
        st_upper = st_short.upper()
        sec_raw = str(rec.get("section", "")).strip()
        sec_norm = re.match(r'(\d+[A-Za-z]*)', sec_raw)
        sec_clean = sec_norm.group(1).upper() if sec_norm else sec_raw.upper()
        
        heading_lower = rec.get("heading", "").lower()
        text_lower = rec.get("text", "")[:500].lower()

        active_statutes = set(issue_analysis.get("active_statutes", []))
        targeted_sections = issue_analysis.get("targeted_sections", {})
        negative_distractors = set((d[0].upper(), str(d[1]).upper()) for d in issue_analysis.get("negative_distractors", []))

        # 1. Distractor Penalty (Direct negative discrimination)
        if (st_upper, sec_clean) in negative_distractors:
            return -self.w_distract

        # 2. Statute Scope Score
        statute_score = 0.0
        if st_upper in active_statutes:
            statute_score = 1.0
        else:
            # If statute is not in active statutes for this query, penalize heavily
            if active_statutes:
                return -50.0

        # 3. Concept & Target Section Score
        concept_score = 0.0
        st_targets = [str(s).upper() for s in targeted_sections.get(st_upper, [])]
        if sec_clean in st_targets or sec_raw.upper() in st_targets:
            concept_score = 1.0

        # 4. Heading Relevance Score
        heading_score = 0.0
        for kw in query_words:
            if len(kw) > 3 and kw in heading_lower:
                heading_score += 0.3
        heading_score = min(1.0, heading_score)

        # Compound key phrase in heading
        for phrase in [
            "electronic record", "certificate", "attachment of property", "proceeds of crime",
            "police custody", "remand", "bail", "undertrial", "sexual harassment", "sexual assault",
            "penetrative sexual assault", "mandatory reporting", "forgery", "criminal breach of trust",
            "cheating", "private defence", "death by negligence", "rash driving", "snatching",
            "extortion", "robbery", "dacoity", "dishonest misappropriation", "counterfeiting", "defamation"
        ]:
            if phrase in heading_lower and (phrase in query.lower() or any(w in query_words for w in phrase.split())):
                heading_score = max(heading_score, 1.0)
                break

        # 5. Fact Alignment Score
        fact_score = 0.0
        all_issues = issue_analysis.get("primary_issues", []) + issue_analysis.get("secondary_issues", [])
        for issue in all_issues:
            if issue["statute"] == st_upper and (sec_clean in issue["target_sections"] or sec_raw in issue["target_sections"]):
                fact_score += len(issue.get("fact_triggers", [])) * 0.5
        fact_score = min(1.0, fact_score)

        # 6. Issue Branch Score
        branch_score = 1.0 if st_upper in active_statutes else 0.0

        # 7. Subsection Score
        subsec_score = 0.0
        if "(" in sec_raw:
            subsec_score = 0.5

        # 8. Lexical Score
        lexical_score = 0.0
        for kw in query_words:
            if len(kw) > 3 and kw in text_lower:
                lexical_score += 0.1
        lexical_score = min(1.0, lexical_score)

        # Generic Section 1 & 2 penalty unless specifically requested
        if sec_clean in ["1", "2"] and not any(w in query_words for w in ["definition", "title", "commencement", "scope", "2(1)(d)"]):
            lexical_score -= 0.8

        final_score = (
            self.w_lexical * lexical_score
          + self.w_statute * statute_score
          + self.w_concept * concept_score
          + self.w_heading * heading_score
          + self.w_fact * fact_score
          + self.w_branch * branch_score
          + self.w_subsec * subsec_score
        )

        return final_score

    def rerank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
        query_words: Set[str],
        issue_analysis: Dict[str, Any]
    ) -> List[Tuple[float, Dict[str, Any]]]:
        scored = []
        for rec in candidates:
            sc = self.score_candidate(rec, query, query_words, issue_analysis)
            scored.append((sc, rec))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
