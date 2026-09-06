# test_experimental_modules.py — Unit Tests for Phase 8.2G Experimental Retrieval Components

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from retrieval.experimental.issue_decomposer import LegalIssueDecomposer
from retrieval.experimental.legal_concept_expander import LegalConceptExpander
from retrieval.experimental.parallel_statute_retriever import ParallelStatuteRetriever
from retrieval.experimental.legal_reranker import LegalReranker
from retrieval.experimental.evidence_sufficiency import EvidenceSufficiencyEvaluator

def test_pipeline():
    print("=== Testing Experimental Components ===")
    
    query = "A cashier secretly pocketed cash from retail register, police arrested without notice and seized CCTV hard drive"
    print(f"Query: {query}\n")

    # 1. Issue Decomposer
    decomposer = LegalIssueDecomposer()
    decomp = decomposer.decompose_query(query)
    print(f"1. Decomposed Issues ({decomp['issue_count']}):")
    for iss in decomp["issues"]:
        print(f"   - {iss['issue_type']}: statutes={iss['statute_candidates']}, concepts={iss['matched_concepts']}")

    # 2. Concept Expander
    expander = LegalConceptExpander()
    expanded = expander.expand_query(query)
    print(f"\n2. Concept Expansion (confidence={expanded['confidence']}):")
    print(f"   Concepts: {expanded['concepts_detected']}")
    print(f"   Expanded queries: {expanded['expanded_retrieval_queries']}")

    # 3. Parallel Statute Retriever
    retriever = ParallelStatuteRetriever()
    parallel_res = retriever.retrieve_parallel_branches(query, per_statute_k=3)
    print(f"\n3. Parallel Branches Retrieved ({parallel_res['candidate_count']} candidates):")
    for st, items in parallel_res["branch_results"].items():
        secs = [f"{i['statute']} {i['section']} (score={i['score']})" for i in items]
        print(f"   - {st}: {secs}")

    # 4. Legal Reranker
    reranker = LegalReranker()
    reranked = reranker.rerank_candidates(query, parallel_res["candidates"], decomp["issues"], top_k=6)
    print(f"\n4. Reranked Candidates (Top 6):")
    for r in reranked:
        print(f"   Rank {r['rank']}: {r['statute']} Section {r['section']} (Score={r['score']}) | Heading: {r['heading'][:45]}...")

    # 5. Evidence Sufficiency Check
    evaluator = EvidenceSufficiencyEvaluator()
    sufficiency = evaluator.evaluate_sufficiency(decomp["issues"], reranked)
    print(f"\n5. Evidence Sufficiency Check: {sufficiency['overall_status']} (Ratio: {sufficiency['sufficiency_ratio']})")
    for eval_item in sufficiency["issue_evaluations"]:
        print(f"   - Issue: {eval_item['issue']} -> Status: {eval_item['status']} ({eval_item['reason']})")

    assert len(decomp["issues"]) > 0
    assert len(parallel_res["candidates"]) > 0
    # Branch consumers historically read `score`; ranking consumers read the
    # explicit `branch_score`. Both must remain present and semantically equal.
    for candidate in parallel_res["candidates"]:
        assert candidate["score"] == candidate["branch_score"]
    assert len(reranked) > 0
    print("\n✅ All Experimental Unit Tests Passed Successfully!")

if __name__ == "__main__":
    test_pipeline()
