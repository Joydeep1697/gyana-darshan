"""Deterministic clarification checks for legally material missing facts."""

from __future__ import annotations

import re


_DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+\d{4}|(?:19|20)\d{2})\b",
    re.IGNORECASE,
)


def clarification_questions(query: str) -> list[str]:
    """Return only questions whose answers can materially change legal routing."""
    normalized = " ".join(query.split())
    lower = normalized.casefold()
    questions: list[str] = []

    transition_signal = any(
        phrase in lower
        for phrase in (
            "old law", "new law", "which law", "which code", "transition",
            "ipc or bns", "crpc or bnss", "iea or bsa", "fir came later",
            "before commencement", "after commencement",
        )
    )
    if transition_signal and not _DATE_PATTERN.search(normalized):
        questions.append(
            "What was the date of the alleged conduct, and when was the FIR or proceeding started?"
        )

    if any(term in lower for term in ("court", "high court", "jurisdiction", "file a case")):
        has_location = bool(re.search(r"\b(?:in|at|within)\s+[A-Z][A-Za-z .-]{2,}\b", normalized))
        if not has_location:
            questions.append("Which State or court jurisdiction is involved?")

    if any(term in lower for term in ("minor", "child", "underage", "pocso")):
        has_age = bool(re.search(r"\b(?:aged?|age)\s*(?:of\s*)?\d{1,2}\b|\b\d{1,2}[- ]year[- ]old\b", lower))
        if not has_age:
            questions.append("What was the person's age on the date of the alleged conduct?")

    return questions[:2]
