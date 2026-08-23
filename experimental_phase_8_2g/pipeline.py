# pipeline.py — Phase 8.2G Experimental Retrieval & Legal Reasoning Pipeline
#
# Objective:
# End-to-end integration of experimental legal retrieval modules:
# 1. Legal Issue Decomposition (Agent 4)
# 2. Legal Concept Expansion (Agent 5)
# 3. Parallel Statute Retrieval (Agent 6)
# 4. Multi-Factor Explainable Legal Reranking (Agent 7)
# 5. Evidence Sufficiency Verification (Agent 9)
# 6. Structured Experimental Grounded Legal Answer Synthesis

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.experimental.issue_decomposer import LegalIssueDecomposer
from retrieval.experimental.legal_concept_expander import LegalConceptExpander
from retrieval.experimental.parallel_statute_retriever import ParallelStatuteRetriever
from retrieval.experimental.legal_reranker import LegalReranker
from retrieval.experimental.evidence_sufficiency import EvidenceSufficiencyEvaluator

class ExperimentalLegalPipeline:
    """Integrated experimental pipeline for issue-decomposed multi-statute legal retrieval."""

    def __init__(self):
        self.decomposer = LegalIssueDecomposer()
        self.expander = LegalConceptExpander()
        self.parallel_retriever = ParallelStatuteRetriever()
        self.reranker = LegalReranker()
        self.sufficiency_evaluator = EvidenceSufficiencyEvaluator()

    def process_query(self, query: str, per_statute_k: int = 4, top_k_final: int = 8) -> Dict[str, Any]:
        """Execute full experimental retrieval and evidence synthesis pipeline."""
        # Step 1: Issue Decomposition
        decomposition = self.decomposer.decompose_query(query)

        # Step 2: Concept Expansion
        expansion = self.expander.expand_query(query)

        # Step 3: Parallel Statute Retrieval
        parallel_results = self.parallel_retriever.retrieve_parallel_branches(query, per_statute_k=per_statute_k)

        # Step 4: Candidate Reranking
        reranked_candidates = self.reranker.rerank_candidates(
            query=query,
            candidates=parallel_results["candidates"],
            issues=decomposition["issues"],
            top_k=top_k_final
        )

        # Step 5: Evidence Sufficiency Evaluation
        sufficiency = self.sufficiency_evaluator.evaluate_sufficiency(
            issues=decomposition["issues"],
            reranked_evidence=reranked_candidates
        )

        # Step 6: Format Grounded Evidence Pack and Legal Answer
        evidence_pack = self._format_evidence_pack(query, reranked_candidates, sufficiency)
        synthesized_answer = self._synthesize_grounded_answer(query, decomposition, reranked_candidates, sufficiency)

        return {
            "query": query,
            "decomposition": decomposition,
            "concept_expansion": expansion,
            "parallel_branches": parallel_results["branch_results"],
            "retrieved_sections": reranked_candidates,
            "evidence_sufficiency": sufficiency,
            "evidence_pack": evidence_pack,
            "answer": synthesized_answer
        }

    def _format_evidence_pack(self, query: str, candidates: List[Dict[str, Any]], sufficiency: Dict[str, Any]) -> str:
        lines = [
            f"=== EXPERIMENTAL PHASE 8.2G AUTHORITATIVE EVIDENCE PACK ===",
            f"Query: {query}",
            f"Evidence Grounding Status: {sufficiency['overall_status']} (Sufficiency: {sufficiency['sufficiency_ratio']*100:.0f}%)",
            f"============================================================"
        ]
        for c in candidates:
            lines.append(f"\n[Rank {c['rank']}] {c['statute']} Section {c['section']}")
            if c.get("heading"):
                lines.append(f"Heading: {c['heading']}")
            lines.append(f"Ranking Score: {c['score']} (Factors: {', '.join(c['ranking_factors'][:2])})")
            lines.append(f"Text: {c.get('text', '')[:250]}...")
        return "\n".join(lines)

    def _synthesize_grounded_answer(self, query: str, decomposition: Dict[str, Any], candidates: List[Dict[str, Any]], sufficiency: Dict[str, Any]) -> str:
        statute_citations = []
        for c in candidates[:4]:
            statute_citations.append(f"{c['statute']} Section {c['section']}")

        cit_str = ", ".join(statute_citations) if statute_citations else "applicable provisions"
        
        issue_summaries = []
        for iss in decomposition["issues"]:
            if iss["issue_type"] != "MULTI_STATUTE":
                issue_summaries.append(f"{iss['issue_type']} (governed by {', '.join(iss['statute_candidates'])})")

        issue_text = "; ".join(issue_summaries[:3]) if issue_summaries else "legal rights and liabilities"

        answer = (
            f"Based on authoritative statutory provisions grounded in the Official Gazette ({cit_str}), "
            f"the factual scenario discloses {issue_text}. "
            f"The legal determination is supported with an evidence sufficiency status of {sufficiency['overall_status']}. "
            f"Under the codified provisions, all statutory requirements and evidentiary procedural safeguards must be strictly satisfied."
        )
        return answer
