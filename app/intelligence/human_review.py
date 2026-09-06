"""Deterministic, auditable escalation guidance for low-confidence legal answers."""

from __future__ import annotations

from dataclasses import dataclass

from app.intelligence.grounding_verdict import ClaimCriticality, GroundingVerdict


@dataclass(frozen=True)
class HumanReviewRecommendation:
    required: bool
    priority: str | None = None
    reason: str | None = None


def recommend_human_review(verdict: GroundingVerdict) -> HumanReviewRecommendation:
    """Require review until independent proposition verification is available.

    A legacy or inconsistent verified label must not suppress escalation.
    """
    if verdict.status in {"CLARIFICATION_REQUIRED", "INPUT_NEEDS_CORRECTION"}:
        return HumanReviewRecommendation(False)
    has_critical_claim = any(item.criticality == ClaimCriticality.CRITICAL for item in verdict.claims)
    if verdict.status == "EVIDENCE_CONFLICT":
        return HumanReviewRecommendation(True, "HIGH", "Retrieved authorities conflict; obtain qualified legal review before relying on this answer.")
    if has_critical_claim:
        return HumanReviewRecommendation(True, "HIGH", "The answer contains a material legal consequence that is not fully verified.")
    return HumanReviewRecommendation(True, "STANDARD", "The answer is not fully verified; confirm the cited authorities before relying on it.")
