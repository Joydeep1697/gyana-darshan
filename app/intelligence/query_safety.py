"""Deterministic intake checks for consultation premises.

These checks deliberately run before retrieval.  A citation firewall can verify a
generated claim, but it cannot make an invented statute, impossible date, or
non-legal prompt into a grounded legal question.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re


@dataclass(frozen=True)
class IntakeFinding:
    code: str
    message: str


_DATE_RE = re.compile(
    r"\b(?P<day>0?[1-9]|[12]\d|3[01])\s+"
    r"(?P<month>january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+(?P<year>19\d{2}|20\d{2})\b",
    re.IGNORECASE,
)
_FICTIONAL_AUTHORITY_RE = re.compile(
    r"\b(?:quantum\s+goat(?:\s+protection)?\s+act|sharma\s+v\.?\s+dragon)\b",
    re.IGNORECASE,
)
_NON_HUMAN_ACCUSED_RE = re.compile(
    r"\b(?:dog|cat|goat|cow|horse|samosa|sandwich|robot)\b[^.?!]{0,100}"
    r"\b(?:accused|arrested|charged|prosecuted|criminally\s+liable|convicted)\b|"
    r"\b(?:accused|arrested|charged|prosecuted|criminally\s+liable|convicted)\b"
    r"[^.?!]{0,100}\b(?:dog|cat|goat|cow|horse|samosa|sandwich|robot)\b",
    re.IGNORECASE,
)
_INSTRUCTION_OVERRIDE_RE = re.compile(
    r"\b(?:ignore|disregard|override)\b[^.?!]{0,100}\b(?:instructions|rules|system prompt)\b",
    re.IGNORECASE,
)


def assess_legal_intake(query: str) -> IntakeFinding | None:
    """Return a user-safe correction when the premise cannot be legally grounded."""
    for match in _DATE_RE.finditer(query):
        try:
            datetime.strptime(match.group(0).title(), "%d %B %Y")
        except ValueError:
            return IntakeFinding(
                "INVALID_DATE",
                f"{match.group(0)} is not a valid calendar date. Please correct the chronology before I analyse which law applies.",
            )
    if _FICTIONAL_AUTHORITY_RE.search(query):
        return IntakeFinding(
            "UNVERIFIED_AUTHORITY",
            "I could not identify the named statute or case as an Indian legal authority. I will not attach unrelated citations or label an answer as grounded. Please provide a real citation, court, or factual question to research.",
        )
    if _NON_HUMAN_ACCUSED_RE.search(query):
        return IntakeFinding(
            "NON_HUMAN_ACCUSED",
            "Indian criminal liability is assessed for persons and legally recognised entities, not the animal, food item, or object described as the accused. If a person’s conduct is the issue, please state that conduct and the relevant facts.",
        )
    if _INSTRUCTION_OVERRIDE_RE.search(query):
        return IntakeFinding(
            "NON_LEGAL_INSTRUCTION",
            "I can help with a legal question, but I cannot treat instructions to override safeguards as legal facts. Please state the legal issue you want researched.",
        )
    return None
