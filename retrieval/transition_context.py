"""Deterministic timeline classification for India's 1 July 2024 criminal-law transition.

The date of the alleged conduct answers the substantive-law question.  It does not,
by itself, answer which procedural or evidence statute applies.  Those two questions
turn on whether the relevant investigation/proceeding was already pending immediately
before commencement.  Keeping those axes separate prevents the retriever from mixing
IPC liability with an unqualified BNS offence provision, or BSA evidence rules with a
saved Indian Evidence Act proceeding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


COMMENCEMENT_DATE = date(2024, 7, 1)
DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
DATE_RE = re.compile(
    r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b|"
    r"\b\d{4}-\d{2}-\d{2}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"
)

OFFENCE_TERMS = (
    "offence", "offense", "theft", "assault", "murder", "fraud", "conduct",
    "incident", "occurrence", "committed", "occurred", "alleged act",
)
PROCEDURE_TERMS = (
    "fir", "complaint", "investigation", "arrest", "custody", "remand", "search",
    "seizure", "charge-sheet", "chargesheet", "trial", "inquiry", "application",
    "appeal", "proceeding",
)


@dataclass(frozen=True)
class TransitionContext:
    offence_date: date | None = None
    procedure_start_date: date | None = None
    pending_before_commencement: bool | None = None
    procedure_regime: str = "UNKNOWN"
    evidence_regime: str = "UNKNOWN"

    @property
    def is_transition_matter(self) -> bool:
        return bool(
            (self.offence_date and self.offence_date < COMMENCEMENT_DATE)
            or self.pending_before_commencement is not None
        )


def _parse_date(value: str) -> date | None:
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _dated_events(query: str) -> list[tuple[date, str, int, int]]:
    events: list[tuple[date, str, int, int]] = []
    for match in DATE_RE.finditer(query):
        parsed = _parse_date(match.group(0))
        if parsed:
            events.append((parsed, match.group(0), match.start(), match.end()))
    return events


def _context(query: str, start: int, end: int, radius: int = 95) -> str:
    return query[max(0, start - radius): min(len(query), end + radius)].lower()


def _is_commencement_reference(raw: str, context: str) -> bool:
    return raw.lower() in {"1 july 2024", "01 july 2024", "01/07/2024", "01-07-2024"} and any(
        token in context
        for token in ("commence", "commencement", "came into force", "new criminal law", "before", "after")
    )


def analyze_transition(query: str) -> TransitionContext:
    """Classify substantive, procedural, and evidence timing without conflating them."""
    lower = query.lower()
    events = _dated_events(query)

    offence_candidates: list[date] = []
    procedure_candidates: list[date] = []
    for parsed, raw, start, end in events:
        around = _context(query, start, end)
        if _is_commencement_reference(raw, around):
            continue
        if any(term in around for term in OFFENCE_TERMS):
            offence_candidates.append(parsed)
        if any(term in around for term in PROCEDURE_TERMS):
            procedure_candidates.append(parsed)

    # A narrative with an alleged offence and several dates ordinarily states the
    # conduct first.  Use the earliest pre-commencement date only as a conservative
    # fallback when the local date window could not disambiguate it.
    offence_date = min(offence_candidates) if offence_candidates else None
    if offence_date is None and events and any(term in lower for term in OFFENCE_TERMS):
        non_commencement = [
            parsed for parsed, raw, start, end in events
            if not _is_commencement_reference(raw, _context(query, start, end))
        ]
        pre_dates = [value for value in non_commencement if value < COMMENCEMENT_DATE]
        offence_date = min(pre_dates) if pre_dates else (min(non_commencement) if non_commencement else None)

    # Do not let the offence date masquerade as a procedural start date merely
    # because a long composite sentence mentions an FIR nearby.
    procedure_candidates = [value for value in procedure_candidates if value != offence_date]
    procedure_start = min(procedure_candidates) if procedure_candidates else None

    explicit_pending = bool(re.search(
        r"(?:investigation|trial|inquiry|appeal|application|proceeding|fir)"
        r"[^.\n]{0,80}\b(?:already\s+)?pending\b[^.\n]{0,80}\b(?:before|immediately before)\s+"
        r"(?:1|01)\s+july\s+2024",
        lower,
    )) or "pending immediately before 1 july 2024" in lower
    explicit_not_pending = bool(re.search(
        r"\bno\s+(?:investigation|trial|inquiry|appeal|application|proceeding|fir)"
        r"[^.\n]{0,60}\bpending\b[^.\n]{0,60}\bbefore\s+(?:1|01)\s+july\s+2024",
        lower,
    ))

    post_start_language = bool(re.search(
        r"(?:fir|complaint|investigation|trial|inquiry|application|appeal|proceeding)"
        r"[^.\n]{0,80}\b(?:began|started|commenced|registered|filed|instituted|initiated|lodged)\b"
        r"[^.\n]{0,80}\b(?:after|on or after)\s+(?:1|01)\s+july\s+2024",
        lower,
    ))
    pre_start_language = bool(re.search(
        r"(?:fir|complaint|investigation|trial|inquiry|application|appeal|proceeding)"
        r"[^.\n]{0,80}\b(?:began|started|commenced|registered|filed|instituted|initiated|lodged)\b"
        r"[^.\n]{0,80}\b(?:before|prior to)\s+(?:1|01)\s+july\s+2024",
        lower,
    ))

    if explicit_not_pending or post_start_language:
        pending = False
    elif explicit_pending or pre_start_language:
        pending = True
    elif procedure_start is not None:
        pending = procedure_start < COMMENCEMENT_DATE
    else:
        pending = None

    if pending is True:
        procedure_regime, evidence_regime = "CRPC", "IEA"
    elif pending is False:
        procedure_regime, evidence_regime = "BNSS", "BSA"
    else:
        procedure_regime, evidence_regime = "UNKNOWN", "UNKNOWN"

    return TransitionContext(
        offence_date=offence_date,
        procedure_start_date=procedure_start,
        pending_before_commencement=pending,
        procedure_regime=procedure_regime,
        evidence_regime=evidence_regime,
    )
