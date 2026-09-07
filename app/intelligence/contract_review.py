"""Deterministic contract review helpers for Vault documents."""

from __future__ import annotations

import re
from typing import Any

from app.intelligence.clause_detector import detect_clauses


REQUIRED_NDA_CLAUSES = {
    "confidentiality": "Confidential information definition and handling duties",
    "termination": "Term, expiry, or termination mechanics",
    "governing_law": "Governing law or court jurisdiction",
}

NDA_SIGNALS = re.compile(r"\b(non[-\s]?disclosure|nda|confidential(?:ity)?|disclos(?:er|ing)|recipient)\b", re.I)
MUTUAL_SIGNALS = re.compile(r"\b(mutual|each party|both parties|either party)\b", re.I)
ONE_WAY_SIGNALS = re.compile(r"\b(disclosing party|receiving party|recipient)\b", re.I)
TERM_SIGNALS = re.compile(
    r"\b(?:(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:year|month)s?|perpetual|indefinite|surviv(?:e|al)|until terminated)\b",
    re.I,
)
CARVE_OUT_SIGNALS = re.compile(
    r"\b(public domain|already known|independently developed|rightfully received|required by law|court order)\b",
    re.I,
)
RETURN_DESTROY_SIGNALS = re.compile(r"\b(return|destroy|destruction|delete|erase)\b", re.I)
NEGATED_CARVE_OUT_SIGNALS = re.compile(
    r"\b(?:no|not|without|does\s+not|do\s+not|doesn't)\b.{0,80}\b(?:public domain|already known|independently developed|rightfully received|required by law|court order)\b",
    re.I,
)
RESIDUALS_SIGNALS = re.compile(r"\bresiduals?\b", re.I)
INJUNCTIVE_SIGNALS = re.compile(r"\b(injunctive relief|specific performance|irreparable harm)\b", re.I)


def _normalise_excerpt(text: str, *, limit: int = 900) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _risk_rank(level: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(level, 0)


def _risk(level: str, title: str, explanation: str, excerpt: str = "", clause_type: str = "") -> dict[str, Any]:
    return {
        "level": level,
        "title": title,
        "explanation": explanation,
        "clause_type": clause_type,
        "excerpt": _normalise_excerpt(excerpt),
    }


def _nda_profile(text: str, clauses: list[dict[str, Any]]) -> dict[str, Any]:
    confidentiality_text = " ".join(c["text"] for c in clauses if c.get("type") == "confidentiality")
    base = text[:5000] or confidentiality_text
    is_nda = bool(NDA_SIGNALS.search(base))
    if not is_nda:
        return {
            "detected": False,
            "kind": "general_contract",
            "signals": [],
            "missing": [],
        }

    signals: list[str] = []
    kind = "one_way_or_unclear"
    if MUTUAL_SIGNALS.search(base):
        kind = "mutual"
        signals.append("mutual obligations")
    elif ONE_WAY_SIGNALS.search(base):
        signals.append("one-way disclosure language")
    has_term = bool(TERM_SIGNALS.search(base))
    if has_term:
        signals.append("term or survival period")
    has_standard_carveouts = bool(CARVE_OUT_SIGNALS.search(base) and not NEGATED_CARVE_OUT_SIGNALS.search(base))
    if has_standard_carveouts:
        signals.append("standard confidentiality carve-outs")
    if RETURN_DESTROY_SIGNALS.search(base):
        signals.append("return or destruction duty")
    if RESIDUALS_SIGNALS.search(base):
        signals.append("residual knowledge language")
    if INJUNCTIVE_SIGNALS.search(base):
        signals.append("injunctive relief language")

    present_types = {c.get("type") for c in clauses}
    missing: list[str] = []
    for clause_type, label in REQUIRED_NDA_CLAUSES.items():
        if clause_type == "termination" and has_term:
            continue
        if clause_type not in present_types:
            missing.append(label)
    if not has_standard_carveouts:
        missing.append("Standard exclusions for public, already known, independently developed, or legally compelled disclosures")
    if not RETURN_DESTROY_SIGNALS.search(base):
        missing.append("Return or destruction of confidential material")

    return {
        "detected": True,
        "kind": kind,
        "signals": signals,
        "missing": missing,
    }


def review_contract(text: str, *, filename: str = "", category: str = "") -> dict[str, Any]:
    """Review a contract using only provided document text and deterministic checks."""
    source_text = text or ""
    clauses = detect_clauses(source_text, category or filename)
    clause_types = {clause.get("type") for clause in clauses}
    nda = _nda_profile(source_text, clauses)

    risks: list[dict[str, Any]] = []
    for clause in clauses:
        level = clause.get("risk", "low")
        if level in {"medium", "high"}:
            risks.append(
                _risk(
                    level,
                    f"{clause.get('type', 'clause').replace('_', ' ').title()} needs review",
                    "The clause contains language commonly associated with elevated negotiation or operational risk.",
                    clause.get("text", ""),
                    clause.get("type", ""),
                )
            )

    if "limitation_of_liability" not in clause_types:
        risks.append(
            _risk(
                "medium",
                "Liability cap not found",
                "No limitation-of-liability clause was detected. For a commercial contract, absence of a cap can materially change exposure.",
                clause_type="limitation_of_liability",
            )
        )
    if "governing_law" not in clause_types:
        risks.append(
            _risk(
                "medium",
                "Governing law not found",
                "No governing-law or jurisdiction clause was detected in the extracted text.",
                clause_type="governing_law",
            )
        )
    if "arbitration" not in clause_types:
        risks.append(
            _risk(
                "low",
                "Dispute-resolution forum not found",
                "No arbitration, mediation, or dispute-resolution clause was detected.",
                clause_type="arbitration",
            )
        )
    if nda["detected"]:
        if nda["kind"] == "one_way_or_unclear":
            risks.append(
                _risk(
                    "medium",
                    "NDA appears one-way or unclear",
                    "The extracted confidentiality language does not clearly show mutual obligations. Confirm whether this should be mutual.",
                    confidentiality_text if (confidentiality_text := " ".join(c["text"] for c in clauses if c.get("type") == "confidentiality")) else "",
                    "confidentiality",
                )
            )
        for missing in nda["missing"]:
            risks.append(
                _risk(
                    "medium",
                    f"NDA missing check: {missing}",
                    "This expected NDA protection was not detected in the extracted text.",
                    clause_type="confidentiality",
                )
            )

    risk_order = sorted(risks, key=lambda item: _risk_rank(item["level"]), reverse=True)
    high = sum(1 for item in risk_order if item["level"] == "high")
    medium = sum(1 for item in risk_order if item["level"] == "medium")
    overall = "high" if high else "medium" if medium else "low"
    summary = (
        f"Detected {len(clauses)} clause type{'s' if len(clauses) != 1 else ''} and "
        f"{len(risk_order)} review issue{'s' if len(risk_order) != 1 else ''}. "
        "This is a document-grounded triage, not legal approval to sign."
    )

    return {
        "filename": filename,
        "document_type": "nda" if nda["detected"] else "contract",
        "overall_risk": overall,
        "summary": summary,
        "clauses": [
            {
                "type": clause.get("type", "unknown"),
                "risk": clause.get("risk", "low"),
                "page": clause.get("page"),
                "excerpt": _normalise_excerpt(clause.get("text", "")),
            }
            for clause in clauses
        ],
        "risks": risk_order,
        "nda": nda,
        "review_recommended": True,
        "review_reason": "Have a qualified lawyer review the underlying contract text before signing or relying on this triage.",
    }

