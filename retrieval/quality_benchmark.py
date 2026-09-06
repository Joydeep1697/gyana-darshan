"""Repeatable, transparent retrieval quality measurements for core legal workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


CitationKey = tuple[str, str]


@dataclass(frozen=True)
class RetrievalBenchmarkCase:
    name: str
    query: str
    expected: frozenset[CitationKey]


@dataclass(frozen=True)
class RetrievalBenchmarkResult:
    case_count: int
    recall_at_k: float
    precision_at_k: float
    mean_reciprocal_rank: float
    missed_authorities: dict[str, tuple[CitationKey, ...]]


class EvidenceRetriever(Protocol):
    def retrieve_evidence_pack(self, query: str, top_k: int = 4) -> dict[str, Any]: ...


CORE_RETRIEVAL_CASES = (
    RetrievalBenchmarkCase(
        "electronic_fir",
        "Can an FIR be filed electronically?",
        frozenset({("BNSS", "173")}),
    ),
    RetrievalBenchmarkCase(
        "pre_commencement_theft",
        "A theft occurred on 29 June 2024. Which law applies?",
        frozenset({("IPC", "378"), ("IPC", "379"), ("BNS", "358"), ("BNSS", "531")} ),
    ),
    RetrievalBenchmarkCase(
        "electronic_record_admissibility",
        "Are electronic records admissible?",
        frozenset({("BSA", "61"), ("BSA", "63")} ),
    ),
)


def _citation_key(record: dict[str, Any]) -> CitationKey | None:
    statute = str(record.get("short_name") or "").upper().strip()
    section = str(record.get("section") or "").split("(", 1)[0].upper().strip()
    return (statute, section) if statute and section else None


def evaluate_retrieval(retriever: EvidenceRetriever, cases: tuple[RetrievalBenchmarkCase, ...] = CORE_RETRIEVAL_CASES, *, k: int = 6) -> RetrievalBenchmarkResult:
    """Measure authority retrieval, retaining every missed citation for review."""
    if k < 1:
        raise ValueError("k must be positive")
    if not cases:
        return RetrievalBenchmarkResult(0, 0.0, 0.0, 0.0, {})

    recall_total = precision_total = reciprocal_rank_total = 0.0
    misses: dict[str, tuple[CitationKey, ...]] = {}
    for case in cases:
        pack = retriever.retrieve_evidence_pack(case.query, top_k=k)
        retrieved = [key for item in pack.get("retrieved_sections", []) if (key := _citation_key(item))]
        relevant = [key for key in retrieved if key in case.expected]
        recall_total += len(set(relevant)) / len(case.expected)
        precision_total += len(relevant) / len(retrieved) if retrieved else 0.0
        first_rank = next((index for index, key in enumerate(retrieved, start=1) if key in case.expected), None)
        reciprocal_rank_total += 1 / first_rank if first_rank else 0.0
        missing = tuple(sorted(case.expected - set(retrieved)))
        if missing:
            misses[case.name] = missing
    count = len(cases)
    return RetrievalBenchmarkResult(
        count,
        round(recall_total / count, 4),
        round(precision_total / count, 4),
        round(reciprocal_rank_total / count, 4),
        misses,
    )
