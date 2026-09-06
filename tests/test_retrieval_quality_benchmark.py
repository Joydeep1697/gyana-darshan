"""Regression tests for repeatable retrieval measurements and review escalation."""

from app.intelligence.grounding_verdict import ClaimCriticality, ClaimStatus, ClaimVerdict, GroundingVerdict
from app.intelligence.human_review import recommend_human_review
from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from retrieval.quality_benchmark import RetrievalBenchmarkCase, evaluate_retrieval


class _FakeRetriever:
    def retrieve_evidence_pack(self, query: str, top_k: int = 4):
        return {"retrieved_sections": [
            {"short_name": "BNSS", "section": "173"},
            {"short_name": "BNSS", "section": "174"},
        ]}


def test_benchmark_reports_recall_precision_rank_and_the_exact_miss():
    result = evaluate_retrieval(_FakeRetriever(), (
        RetrievalBenchmarkCase("case", "query", frozenset({("BNSS", "173"), ("BNSS", "175")})),
    ), k=2)
    assert result.recall_at_k == 0.5
    assert result.precision_at_k == 0.5
    assert result.mean_reciprocal_rank == 1.0
    assert result.missed_authorities == {"case": (("BNSS", "175"),)}


def test_core_benchmark_retrieves_required_authorities_from_real_local_corpus():
    result = evaluate_retrieval(AuthoritativeLegalRetriever(), k=6)
    assert result.case_count == 3
    assert result.recall_at_k == 1.0
    assert result.mean_reciprocal_rank == 1.0
    assert result.missed_authorities == {}


def test_human_review_escalates_conflicts_and_critical_unverified_claims():
    critical = ClaimVerdict("The accused is guilty.", ClaimStatus.UNSUPPORTED, (), ClaimCriticality.CRITICAL)
    assert recommend_human_review(GroundingVerdict("EVIDENCE_CONFLICT", (critical,))).priority == "HIGH"
    assert recommend_human_review(GroundingVerdict("INSUFFICIENT_EVIDENCE", (critical,))).priority == "HIGH"
    assert recommend_human_review(GroundingVerdict("GROUNDED_AND_VERIFIED", (critical,))).required
