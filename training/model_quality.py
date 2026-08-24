"""Data-audit and release-gate utilities for Nyaya Darshana model training.

This module intentionally has no third-party dependencies so that it can run
before GPU packages are installed and inside Kaggle notebook cells.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


FABRICATED_STATUTE_PATTERNS = (
    r"\bb\.?\s*p\.?\s*singh\s+penal\s+code\b",
    r"\bbordeau(?:x)?(?:[-\s]nariman)?\b",
    r"\bbharatiya\s+smriti\s+sanhita\b",
    r"\bbcriminal\s+procedure\s+code\b",
    r"\bbcrpc\b",
    r"\bmission\s+250\b",
)


@dataclass(frozen=True)
class LegalProbe:
    name: str
    question: str
    required_any: tuple[str, ...]
    forbidden: tuple[str, ...] = ()
    critical: bool = True


LEGAL_PROBES: tuple[LegalProbe, ...] = (
    LegalProbe(
        "ipc_successor",
        "Which statute replaced the Indian Penal Code, 1860? Give its complete name.",
        (r"\bbharatiya\s+nyaya\s+sanhita\b",),
        (r"\bbharatiya\s+nagarik\s+suraksha\s+sanhita\b",),
    ),
    LegalProbe(
        "crpc_successor",
        "Which statute replaced the Code of Criminal Procedure, 1973? Give its complete name.",
        (r"\bbharatiya\s+nagarik\s+suraksha\s+sanhita\b",),
        (r"\bbharatiya\s+nyaya\s+sanhita\s+(?:replaced|governs)\s+(?:the\s+)?(?:code\s+of\s+criminal\s+procedure|crpc)",),
    ),
    LegalProbe(
        "evidence_successor",
        "Which statute replaced the Indian Evidence Act, 1872? Give its complete name.",
        (r"\bbharatiya\s+sakshya\s+adhiniyam\b",),
        (r"\binformation\s+technology\s+act\b",),
    ),
    LegalProbe(
        "pocso_independent",
        "Did the Bharatiya Nyaya Sanhita repeal or replace the POCSO Act, 2012?",
        (r"\b(?:no|not|neither|remains|continues|separate|special)\b",),
        (
            r"\b(?:bns|bharatiya\s+nyaya\s+sanhita)\s+(?:has\s+)?(?:repealed|replaced|subsumed)\s+(?:the\s+)?pocso\b",
        ),
    ),
    LegalProbe(
        "bns_not_procedure",
        "Does the Bharatiya Nyaya Sanhita replace the Code of Criminal Procedure?",
        (r"\b(?:no|not|bnss|bharatiya\s+nagarik\s+suraksha\s+sanhita)\b",),
        (r"\byes\b.{0,80}\b(?:bns|bharatiya\s+nyaya\s+sanhita)\b",),
    ),
    LegalProbe(
        "retrospective_substantive_law",
        "A theft occurred on 29 June 2024, but the FIR was registered on 3 July 2024. Does BNS apply retrospectively merely because the FIR was registered after 1 July?",
        (r"\b(?:ipc|indian\s+penal\s+code|not\s+retrospective|article\s+20\s*\(?1\)?)\b",),
        (r"\bbns\s+(?:applies|must\s+apply)\s+retrospectively\b",),
    ),
    LegalProbe(
        "procedural_savings",
        "Which savings provisions should be considered when an IPC-era offence is investigated after the new criminal laws took effect?",
        (r"\b(?:358|531|savings|repeal)\b",),
        (),
        False,
    ),
    LegalProbe(
        "zero_fir",
        "Can information about a cognizable offence be recorded irrespective of territorial jurisdiction under BNSS?",
        (r"\b(?:zero\s+fir|irrespective\s+of\s+territorial\s+jurisdiction|173)\b",),
        (),
        False,
    ),
    LegalProbe(
        "pocso_age",
        "Under POCSO, can a 17-year-old child's apparent consent automatically defeat the application of the Act?",
        (r"\b(?:no|minor|under\s+18|below\s+18|child)\b",),
        (r"\bconsent\s+(?:automatically\s+)?(?:defeats|bars|negates)\s+pocso\b",),
    ),
    LegalProbe(
        "electronic_evidence",
        "Which new statute governs electronic evidence after the replacement of the Indian Evidence Act?",
        (r"\b(?:bharatiya\s+sakshya\s+adhiniyam|bsa)\b",),
        (r"\bbharatiya\s+nyaya\s+sanhita\s+governs\s+electronic\s+evidence\b",),
    ),
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _matches(pattern: str, value: str) -> bool:
    return bool(re.search(pattern, value, flags=re.IGNORECASE | re.DOTALL))


def record_fingerprint(record: Mapping[str, Any]) -> str:
    text = "\n".join(
        _normalize_text(str(record.get(field, "")))
        for field in ("instruction", "input", "output")
    )
    return sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Dataset file does not exist: {source}")
    records: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {source}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected a JSON object in {source}:{line_number}")
            records.append(value)
    if not records:
        raise ValueError(f"Dataset is empty: {source}")
    return records


def audit_dataset(
    records: Sequence[Mapping[str, Any]],
    *,
    split_name: str,
    minimum_records: int = 1,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    categories: dict[str, int] = {}
    fingerprints: set[str] = set()
    duplicate_count = 0

    if len(records) < minimum_records:
        errors.append(
            f"{split_name} contains {len(records)} records; at least {minimum_records} are required"
        )

    for index, record in enumerate(records, start=1):
        identifier = str(record.get("id", f"row-{index}"))
        instruction = str(record.get("instruction", "")).strip()
        answer = str(record.get("output", "")).strip()
        if not instruction or not answer:
            errors.append(f"{split_name}:{identifier} is missing instruction or output")
            continue

        category = str(record.get("category", "uncategorized"))
        categories[category] = categories.get(category, 0) + 1
        fingerprint = record_fingerprint(record)
        if fingerprint in fingerprints:
            duplicate_count += 1
        fingerprints.add(fingerprint)

        for pattern in FABRICATED_STATUTE_PATTERNS:
            if _matches(pattern, answer):
                errors.append(
                    f"{split_name}:{identifier} contains a known fabricated statute pattern: {pattern}"
                )

        if len(answer) < 20:
            warnings.append(f"{split_name}:{identifier} has a very short completion")

    if duplicate_count:
        warnings.append(f"{split_name} contains {duplicate_count} duplicate examples")
    if len(categories) == 1 and len(records) >= 20:
        warnings.append(f"{split_name} contains only one category")
    if categories and len(records) >= 20:
        dominant_category, dominant_count = max(categories.items(), key=lambda item: item[1])
        if dominant_count / len(records) > 0.70:
            warnings.append(
                f"{split_name} is imbalanced: {dominant_category!r} accounts for "
                f"{dominant_count / len(records):.0%} of examples"
            )

    return {
        "split": split_name,
        "records": len(records),
        "categories": dict(sorted(categories.items())),
        "duplicate_count": duplicate_count,
        "fingerprints": fingerprints,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }


def audit_splits(
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    audits = [
        audit_dataset(train, split_name="train", minimum_records=50),
        audit_dataset(validation, split_name="validation", minimum_records=10),
    ]
    if test is not None:
        audits.append(audit_dataset(test, split_name="test", minimum_records=10))

    errors = [message for audit in audits for message in audit["errors"]]
    warnings = [message for audit in audits for message in audit["warnings"]]
    overlap: dict[str, int] = {}
    for left_index, left in enumerate(audits):
        for right in audits[left_index + 1 :]:
            shared = left["fingerprints"] & right["fingerprints"]
            label = f"{left['split']}__{right['split']}"
            overlap[label] = len(shared)
            if shared:
                errors.append(f"Dataset leakage: {label} share {len(shared)} identical examples")

    safe_audits = []
    for audit in audits:
        safe_audits.append({key: value for key, value in audit.items() if key != "fingerprints"})

    return {
        "splits": safe_audits,
        "overlap": overlap,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }


def score_answer(probe: LegalProbe, answer: str) -> dict[str, Any]:
    normalized = answer.strip()
    missing_required = not any(_matches(pattern, normalized) for pattern in probe.required_any)
    fabricated = [
        pattern
        for pattern in FABRICATED_STATUTE_PATTERNS
        if _matches(pattern, normalized)
    ]
    forbidden = [pattern for pattern in probe.forbidden if _matches(pattern, normalized)]
    passed = bool(normalized) and not missing_required and not fabricated and not forbidden
    return {
        "name": probe.name,
        "question": probe.question,
        "answer": normalized,
        "critical": probe.critical,
        "passed": passed,
        "missing_required": missing_required,
        "fabricated_patterns": fabricated,
        "forbidden_patterns": forbidden,
    }


def evaluate_answers(
    answers: Mapping[str, str],
    *,
    minimum_accuracy: float = 0.9,
    probes: Iterable[LegalProbe] = LEGAL_PROBES,
) -> dict[str, Any]:
    results = [score_answer(probe, answers.get(probe.name, "")) for probe in probes]
    passed_count = sum(item["passed"] for item in results)
    accuracy = passed_count / len(results) if results else 0.0
    critical_failures = [item["name"] for item in results if item["critical"] and not item["passed"]]
    hallucinations = [
        item["name"]
        for item in results
        if item["fabricated_patterns"] or item["forbidden_patterns"]
    ]
    return {
        "total": len(results),
        "passed": passed_count,
        "accuracy": round(accuracy, 4),
        "minimum_accuracy": minimum_accuracy,
        "critical_failures": critical_failures,
        "hallucinations": hallucinations,
        "release_ready": accuracy >= minimum_accuracy and not critical_failures and not hallucinations,
        "results": results,
    }


def probe_manifest() -> list[dict[str, Any]]:
    return [asdict(probe) for probe in LEGAL_PROBES]
