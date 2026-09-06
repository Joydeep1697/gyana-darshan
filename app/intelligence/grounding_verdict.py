"""Conservative answer-level grounding verdicts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum
import re

from app.source_presenter import STATUTE_PATTERNS, extract_citation_keys
from retrieval.legal_reasoning import build_reasoning_plan, verify_answer


class ClaimStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ClaimCriticality(StrEnum):
    STANDARD = "STANDARD"
    CRITICAL = "CRITICAL"


class CitationIdentityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


class JurisdictionStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class TemporalStatus(StrEnum):
    CURRENT = "CURRENT"
    NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
    REPEALED = "REPEALED"
    UNKNOWN = "UNKNOWN"


class AuthorityStatus(StrEnum):
    BINDING = "BINDING"
    PERSUASIVE = "PERSUASIVE"
    IRRELEVANT = "IRRELEVANT"
    UNKNOWN = "UNKNOWN"


class ConflictStatus(StrEnum):
    NO_CONFLICT = "NO_CONFLICT"
    UNRESOLVED = "UNRESOLVED"
    UNKNOWN = "UNKNOWN"


_STATUTE_EFFECTIVE_DATES = {
    "BNS": date(2024, 7, 1),
    "BNSS": date(2024, 7, 1),
    "BSA": date(2024, 7, 1),
    "POCSO": date(2012, 11, 14),
}


class QuoteStatus(StrEnum):
    NOT_PRESENT = "NOT_PRESENT"
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"


class PinpointStatus(StrEnum):
    NOT_PRESENT = "NOT_PRESENT"
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"


class SourceIntegrityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    SUSPECT = "SUSPECT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ClaimVerdict:
    text: str
    status: ClaimStatus
    citations: tuple[tuple[str, str], ...]
    criticality: ClaimCriticality


@dataclass(frozen=True)
class ClaimEvidenceVerification:
    claim_text: str
    citation: tuple[str, str] | None
    source_id: str | None
    evidence_span: str | None
    identity_status: CitationIdentityStatus
    proposition_status: ClaimStatus
    jurisdiction_status: JurisdictionStatus
    temporal_status: TemporalStatus
    quote_status: QuoteStatus
    pinpoint_status: PinpointStatus
    source_integrity_status: SourceIntegrityStatus
    authority_status: AuthorityStatus
    conflict_status: ConflictStatus
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class GroundingVerdict:
    status: str
    claims: tuple[ClaimVerdict, ...]
    evidence_verifications: tuple[ClaimEvidenceVerification, ...] = ()

    @property
    def citation_completeness(self) -> float:
        if not self.claims:
            return 0.0
        supported = sum(item.status == ClaimStatus.SUPPORTED for item in self.claims)
        return supported / len(self.claims)

    @property
    def citation_coverage(self) -> float:
        """Share of material claims with retrieved citation identity, not support."""
        if not self.claims:
            return 0.0
        retrieved_edges = {
            (item.claim_text, item.citation) for item in self.evidence_verifications
            if item.identity_status == CitationIdentityStatus.VERIFIED
        }
        covered = sum(
            bool(item.citations) and all((item.text, citation) in retrieved_edges for citation in item.citations)
            for item in self.claims
        )
        return covered / len(self.claims)


_MATERIAL_LANGUAGE = re.compile(
    r"\b(?:must|shall|may|cannot|applies|governs|requires|permits|prohibits|"
    r"punishable|liable|guilt(?:y)?|innocen(?:t|ce)|illegal|lawful|unlawful|right(?:s)?|"
    r"dut(?:y|ies)|obligation|power(?:s)?|limitation|jurisdiction|deadline|admissible|"
    r"repealed|replaced|proves|establishes|conclusive|held|enforceable|arrest(?:ed)?|"
    r"prosecut(?:ed|able)|exception(?:s)?|interpret(?:ation|ed)|(un)?enforceable)\b",
    re.IGNORECASE,
)
_CRITICAL_LANGUAGE = re.compile(
    r"\b(?:criminal(?:ly)?\s+liable|guilt(?:y)?|innocen(?:t|ce)|arrest(?:ed)?|punishable|"
    r"penalt(?:y|ies)|deadline|limitation|jurisdiction|constitutional|lawful|unlawful|"
    r"prosecut(?:ed|able))\b",
    re.IGNORECASE,
)


def _criticality(text: str) -> ClaimCriticality:
    return ClaimCriticality.CRITICAL if _CRITICAL_LANGUAGE.search(text) else ClaimCriticality.STANDARD


def _material_claims(answer: str) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    claims = []
    for sentence in (part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", answer)):
        if not sentence:
            continue
        citations = tuple(extract_citation_keys(sentence))
        if citations or _MATERIAL_LANGUAGE.search(sentence):
            claims.append((sentence, citations))
    return claims


def _record_key(record: dict) -> tuple[str, str]:
    statute = str(record.get("short_name") or record.get("statute") or "").upper()
    if "NYAYA" in statute:
        statute = "BNS"
    elif "NAGARIK" in statute:
        statute = "BNSS"
    elif "SAKSHYA" in statute:
        statute = "BSA"
    section = re.match(r"\d+[A-Za-z]*", str(record.get("section") or ""))
    return statute, section.group(0).upper() if section else ""


def _parse_lifecycle_date(value: object) -> date | None:
    if not value:
        return None
    for pattern in ("%Y-%m-%d", "%d %B %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value), pattern).date()
        except ValueError:
            continue
    return None


def _authority_status(record: dict | None, jurisdiction: JurisdictionStatus) -> AuthorityStatus:
    """Classify authority only from explicit source metadata or known primary law."""
    if not record or jurisdiction != JurisdictionStatus.VALID:
        return AuthorityStatus.IRRELEVANT if record else AuthorityStatus.UNKNOWN

    authority_type = str(record.get("authority_type") or record.get("source_type") or "").casefold()
    court = str(record.get("court") or "").casefold()
    statute, _ = _record_key(record)
    if statute in _STATUTE_EFFECTIVE_DATES or statute in {"IPC", "CRPC", "IEA", "CONSTITUTION"}:
        return AuthorityStatus.BINDING
    if authority_type in {"statute", "legislation", "central_legislation", "constitution", "supreme_court"}:
        return AuthorityStatus.BINDING
    if "supreme court of india" in court:
        return AuthorityStatus.BINDING
    if authority_type in {"high_court", "tribunal", "judgment", "case_law"} or "high court" in court:
        return AuthorityStatus.PERSUASIVE
    if authority_type in {"commentary", "secondary", "article", "guidance"}:
        return AuthorityStatus.PERSUASIVE
    return AuthorityStatus.UNKNOWN


def _conflicted_record_keys(evidence_records: list[dict] | None) -> set[tuple[str, str]]:
    """Return sources in an explicitly-labelled unresolved evidentiary conflict.

    Conflict detection deliberately relies on producer metadata. Inferring a conflict
    from two snippets' wording would itself be an unverified legal interpretation.
    """
    groups: dict[str, set[str]] = {}
    members: dict[str, list[tuple[str, str]]] = {}
    for record in evidence_records or []:
        group = str(record.get("conflict_group") or "").strip()
        position = str(record.get("proposition_position") or record.get("position") or "").casefold()
        if not group or position not in {"supports", "refutes", "contradicts"}:
            continue
        groups.setdefault(group, set()).add(position)
        members.setdefault(group, []).append(_record_key(record))
    return {
        key
        for group, positions in groups.items()
        if "supports" in positions and ({"refutes", "contradicts"} & positions)
        for key in members[group]
    }


def _normalized_evidence_text(value: object) -> str:
    """Normalize layout noise only; never repair or guess OCR characters."""
    return re.sub(r"\s+", " ", str(value or "").replace("–", "-").replace("—", "-")).strip()


def _pinpoint_spans(text: str, citation: tuple[str, str] | None, source_text: str) -> tuple[str, ...] | None:
    """Resolve every explicit subsection to a unique source span, or fail closed.

    None means no pinpoint; an empty tuple means a pinpoint could not be
    resolved. Nested clauses and ranges need a structured hierarchy and remain
    unverified here. Layout boundaries must be read before whitespace folding.
    """
    if not citation:
        return None
    statute, section = citation
    statute_pattern = STATUTE_PATTERNS.get(statute, re.escape(statute))
    token = r"\d+[A-Za-z]*(?:\s*\([0-9A-Za-z]+\))*"
    group = rf"({token}(?:\s*(?:,|and|&|to|[-–])\s*{token})*)"
    label = r"(?:sections?|secs?\.?|§)\s*"
    patterns = (
        rf"\b{statute_pattern}\b\s*(?:,\s*\d{{4}})?\s*{label}{group}",
        rf"{label}{group}\s+of\s+(?:the\s+)?{statute_pattern}\b",
    )
    requested = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            for value in re.findall(token, match.group(1)):
                root = re.match(r"\d+[A-Za-z]*", value).group(0).upper()
                if root != section or "(" not in value:
                    continue
                suffix = re.sub(r"\s+", "", value[len(root):])
                if not re.fullmatch(r"\(\d+\)", suffix) or re.search(r"\bto\b|[-–]", match.group(1)):
                    return ()
                requested.append(suffix[1:-1])
    if not requested:
        return None

    # A cross-reference can terminate a candidate span, but cannot establish a
    # new subsection. Only line labels or sentence-opening section labels do so.
    marker = re.compile(
        r"\bSection\s+(?P<section>\d+[A-Za-z]*)(?:\s*\((?P<sub>\d+)\))?"
        r"|^[ \t]*\((?P<bare>\d+)\)", re.IGNORECASE | re.MULTILINE,
    )
    markers = list(marker.finditer(source_text))
    spans: dict[str, list[str]] = {}
    current_section = section
    for index, match in enumerate(markers):
        if match.group("section"):
            current_section = match.group("section").upper()
        subsection = match.group("sub") or match.group("bare")
        prefix = source_text[:match.start()].rstrip(" \t")
        structural = not prefix or prefix[-1] in "\n\r.!?"
        if current_section != section or not subsection or not structural:
            continue
        end = markers[index + 1].start() if index + 1 < len(markers) else len(source_text)
        spans.setdefault(subsection, []).append(source_text[match.start():end].strip())
    if any(len(spans.get(subsection, [])) != 1 for subsection in requested):
        return ()
    return tuple(spans[subsection][0] for subsection in dict.fromkeys(requested))


def _source_integrity_status(record: dict | None) -> SourceIntegrityStatus:
    """Require an explicit integrity signal before treating extracted text as audit-grade."""
    if not record:
        return SourceIntegrityStatus.UNKNOWN
    if str(record.get("integrity_status") or "").casefold() == "verified":
        return SourceIntegrityStatus.VERIFIED
    method = str(record.get("extraction_method") or record.get("extraction") or "").casefold()
    confidence = record.get("ocr_confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    if method == "ocr" or confidence is not None:
        return SourceIntegrityStatus.SUSPECT
    source = str(record.get("source") or "").casefold()
    if record.get("curation") and ("official" in source or "india code" in source or "gazette" in source):
        return SourceIntegrityStatus.VERIFIED
    return SourceIntegrityStatus.UNKNOWN


def _verification_records(claims, evidence_records: list[dict] | None, event_date: date | None) -> tuple[ClaimEvidenceVerification, ...]:
    by_key = {_record_key(record): record for record in evidence_records or []}
    conflicted_keys = _conflicted_record_keys(evidence_records)
    records = []
    for text, citations in claims:
        quoted = re.findall(r'["“]([^"”]{3,})["”]', text)
        for citation in citations or (None,):
            record = by_key.get(citation) if citation else None
            source_text = str(record.get("text") or "") if record else ""
            pinpoint_spans = _pinpoint_spans(text, citation, source_text)
            pinpoint = (PinpointStatus.NOT_PRESENT if pinpoint_spans is None else
                        PinpointStatus.VERIFIED if pinpoint_spans else PinpointStatus.MISMATCH)
            quote_spans = (source_text,) if pinpoint_spans is None else pinpoint_spans
            identity = CitationIdentityStatus.VERIFIED if record else (
                CitationIdentityStatus.INVALID if citation else CitationIdentityStatus.UNVERIFIED
            )
            quote_status = QuoteStatus.NOT_PRESENT
            if quoted:
                quote_status = QuoteStatus.VERIFIED if record and quote_spans and all(
                    _normalized_evidence_text(value) in _normalized_evidence_text(span)
                    for value in quoted for span in quote_spans
                ) else QuoteStatus.MISMATCH
            integrity = _source_integrity_status(record)
            country = str(record.get("country") or record.get("jurisdiction") or "India") if record else ""
            jurisdiction = JurisdictionStatus.VALID if record and country.casefold() in {"india", "in"} else (
                JurisdictionStatus.INVALID if record and country else JurisdictionStatus.UNKNOWN
            )
            effective_date = _parse_lifecycle_date(record.get("effective_date")) if record else None
            effective_date = effective_date or (_STATUTE_EFFECTIVE_DATES.get(citation[0]) if citation else None)
            repealed_date = _parse_lifecycle_date(record.get("repealed_date")) if record else None
            if repealed_date and (event_date is None or event_date >= repealed_date):
                temporal = TemporalStatus.REPEALED
            elif event_date and effective_date and event_date < effective_date:
                temporal = TemporalStatus.NOT_YET_EFFECTIVE
            elif effective_date:
                temporal = TemporalStatus.CURRENT
            else:
                temporal = TemporalStatus.UNKNOWN
            reasons = []
            if not citation:
                reasons.append("Material claim has no citation.")
            elif not record:
                reasons.append("Cited authority was not retrieved.")
            if quote_status == QuoteStatus.MISMATCH:
                reasons.append("Quoted text was not found within every cited evidence span.")
            if pinpoint == PinpointStatus.MISMATCH:
                reasons.append("Cited pinpoint could not be resolved to a unique source span.")
            if integrity == SourceIntegrityStatus.SUSPECT:
                reasons.append("Source text is OCR-derived or has unverified extraction confidence.")
            elif integrity == SourceIntegrityStatus.UNKNOWN:
                reasons.append("Source text integrity is not verified by retrieval metadata.")
            if jurisdiction == JurisdictionStatus.INVALID:
                reasons.append("Source jurisdiction is not India.")
            if temporal == TemporalStatus.NOT_YET_EFFECTIVE:
                reasons.append("Source was not yet effective on the relevant event date.")
            if temporal == TemporalStatus.REPEALED:
                reasons.append("Source was repealed on the relevant event date.")
            authority = _authority_status(record, jurisdiction)
            conflict = ConflictStatus.UNRESOLVED if citation in conflicted_keys else (
                ConflictStatus.NO_CONFLICT if record else ConflictStatus.UNKNOWN
            )
            if authority == AuthorityStatus.IRRELEVANT:
                reasons.append("Source is not an applicable Indian authority for this question.")
            elif authority == AuthorityStatus.UNKNOWN:
                reasons.append("Source authority level is not verified from retrieval metadata.")
            if conflict == ConflictStatus.UNRESOLVED:
                reasons.append("Retrieved sources contain an unresolved conflict on this proposition.")
            # Source identity and quotation matching are not proposition proof.
            # This applies equally to templates and model-generated answers.
            reasons.append("The legal proposition has not been independently verified.")
            proposition = ClaimStatus.INSUFFICIENT_EVIDENCE if record else ClaimStatus.UNSUPPORTED
            records.append(ClaimEvidenceVerification(
                text, citation, str(record.get("id")) if record and record.get("id") else None,
                ("\n".join(pinpoint_spans) if pinpoint_spans is not None else source_text) or None,
                identity, proposition, jurisdiction, temporal,
                quote_status, pinpoint, integrity, authority, conflict, tuple(reasons),
            ))
    return tuple(records)


def assess_grounding(query: str, answer: str, evidence_context: str, firewall_passed: bool, deterministic_answer: str | None = None, evidence_records: list[dict] | None = None) -> GroundingVerdict:
    """Fail closed until independent proposition proof is available.

    evidence_context and deterministic_answer remain accepted for compatibility,
    but neither generator text nor template equality is verification evidence.
    Source checks remain available separately from proposition support.
    """
    plan = build_reasoning_plan(query)
    claims = _material_claims(answer)
    citation_issues = verify_answer(answer, plan, [])
    verification_records = _verification_records(claims, evidence_records, plan.offence_date)
    if not firewall_passed or citation_issues["contradictions"] or any(
        item.conflict_status == ConflictStatus.UNRESOLVED for item in verification_records
    ):
        return GroundingVerdict("EVIDENCE_CONFLICT", tuple(
            ClaimVerdict(text, ClaimStatus.CONTRADICTED, citations, _criticality(text)) for text, citations in claims
        ), verification_records)

    retrieved_edges = {
        (item.claim_text, item.citation) for item in verification_records
        if item.identity_status == CitationIdentityStatus.VERIFIED
    }
    verdicts = tuple(
        ClaimVerdict(
            text,
            ClaimStatus.INSUFFICIENT_EVIDENCE if citations and all(
                (text, citation) in retrieved_edges for citation in citations
            ) else ClaimStatus.UNSUPPORTED,
            citations,
            _criticality(text),
        )
        for text, citations in claims
    )
    return GroundingVerdict(
        "INSUFFICIENT_EVIDENCE",
        verdicts, verification_records,
    )


def historical_grounding_verdict(answer: str, recorded_status: str | None) -> GroundingVerdict:
    """Project a saved answer conservatively without modifying its audit record.

    History contains excerpts, not independent proposition or provenance proof.
    Retain recorded conflict/input states; do not promote old success labels.
    """
    if recorded_status in {"CLARIFICATION_REQUIRED", "INPUT_NEEDS_CORRECTION"}:
        return GroundingVerdict(recorded_status, ())
    verdict = assess_grounding("", answer, "", True)
    if recorded_status == "EVIDENCE_CONFLICT":
        return replace(verdict, status="EVIDENCE_CONFLICT")
    return verdict
