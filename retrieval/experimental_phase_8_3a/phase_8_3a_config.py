# phase_8_3a_config.py — Configuration Structure for Phase 8.3A Statute-Aware Preservation
#
# Objective:
# Centralize experimental calibration values and configuration presets for:
# Configuration A: Phase 8.2G baseline behavior (no preservation protection)
# Configuration B: Active statute strongest candidate hard preservation
# Configuration C: Evidence-sufficiency and issue-relevance threshold-gated preservation
# Configuration D: Calibrated preservation bonus / ranking multiplier

from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Phase83AConfig:
    name: str
    mode: str  # "CONFIG_A", "CONFIG_B", "CONFIG_C", "CONFIG_D"
    description: str
    minimum_issue_relevance: float = 0.20
    minimum_retrieval_score: float = 15.0
    minimum_evidence_score: float = 10.0
    branch_preservation_threshold: float = 25.0
    maximum_protected_candidates: int = 3
    preservation_bonus_multiplier: float = 0.25
    max_preservation_bonus: float = 30.0
    per_statute_k: int = 5
    top_k_final: int = 8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode,
            "description": self.description,
            "minimum_issue_relevance": self.minimum_issue_relevance,
            "minimum_retrieval_score": self.minimum_retrieval_score,
            "minimum_evidence_score": self.minimum_evidence_score,
            "branch_preservation_threshold": self.branch_preservation_threshold,
            "maximum_protected_candidates": self.maximum_protected_candidates,
            "preservation_bonus_multiplier": self.preservation_bonus_multiplier,
            "max_preservation_bonus": self.max_preservation_bonus,
            "per_statute_k": self.per_statute_k,
            "top_k_final": self.top_k_final
        }

def get_config_a() -> Phase83AConfig:
    """Configuration A: Phase 8.2G Baseline Behavior (No Statute-Aware Preservation)."""
    return Phase83AConfig(
        name="Configuration A (Phase 8.2G Baseline)",
        mode="CONFIG_A",
        description="Standard global reranking without candidate preservation protection.",
        minimum_issue_relevance=0.0,
        minimum_retrieval_score=0.0,
        minimum_evidence_score=0.0,
        branch_preservation_threshold=0.0,
        maximum_protected_candidates=0,
        preservation_bonus_multiplier=0.0,
        max_preservation_bonus=0.0,
        per_statute_k=5,
        top_k_final=8
    )

def get_config_b() -> Phase83AConfig:
    """Configuration B: Hard Active-Statute Preservation (Strongest Candidate Protected)."""
    return Phase83AConfig(
        name="Configuration B (Active Statute Hard Preservation)",
        mode="CONFIG_B",
        description="Preserve the top local candidate from every active statute branch unconditionally.",
        minimum_issue_relevance=0.05,
        minimum_retrieval_score=1.0,
        minimum_evidence_score=0.0,
        branch_preservation_threshold=1.0,
        maximum_protected_candidates=4,
        preservation_bonus_multiplier=0.0,
        max_preservation_bonus=0.0,
        per_statute_k=5,
        top_k_final=8
    )

def get_config_c() -> Phase83AConfig:
    """Configuration C: Calibrated Threshold-Gated Preservation (Evidence + Relevance)."""
    return Phase83AConfig(
        name="Configuration C (Evidence & Relevance Gated Preservation)",
        mode="CONFIG_C",
        description="Preserve candidates only when issue relevance >= threshold and evidence score >= threshold.",
        minimum_issue_relevance=0.25,
        minimum_retrieval_score=18.0,
        minimum_evidence_score=12.0,
        branch_preservation_threshold=28.0,
        maximum_protected_candidates=3,
        preservation_bonus_multiplier=0.0,
        max_preservation_bonus=0.0,
        per_statute_k=5,
        top_k_final=8
    )

def get_config_d() -> Phase83AConfig:
    """Configuration D: Preservation Multiplier / Global Bonus during Final Ranking."""
    return Phase83AConfig(
        name="Configuration D (Statute Preservation Bonus Multiplier)",
        mode="CONFIG_D",
        description="Soft preservation via calibrated statute preservation bonus added to global score.",
        minimum_issue_relevance=0.20,
        minimum_retrieval_score=15.0,
        minimum_evidence_score=8.0,
        branch_preservation_threshold=20.0,
        maximum_protected_candidates=3,
        preservation_bonus_multiplier=0.35,
        max_preservation_bonus=35.0,
        per_statute_k=5,
        top_k_final=8
    )
