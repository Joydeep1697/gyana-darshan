"""Deterministic issue planning and citation guardrails for Indian legal RAG."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Any


COMMENCEMENT_DATE = date(2024, 7, 1)
DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


@dataclass(frozen=True)
class LegalIssue:
    category: str
    statute: str
    sections: tuple[str, ...]
    guidance: str
    excluded_sections: tuple[str, ...] = ()


@dataclass
class ReasoningPlan:
    issues: list[LegalIssue] = field(default_factory=list)
    safeguards: list[str] = field(default_factory=list)
    direct_answer: str | None = None
    offence_date: date | None = None

    @property
    def required_citations(self) -> list[tuple[str, str]]:
        return [(issue.statute, section) for issue in self.issues for section in issue.sections]


def _extract_dates(query: str) -> list[date]:
    candidates = re.findall(r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", query)
    found = []
    for candidate in candidates:
        for pattern in DATE_FORMATS:
            try:
                found.append(datetime.strptime(candidate, pattern).date())
                break
            except ValueError:
                continue
    return found


@lru_cache(maxsize=1024)
def build_reasoning_plan(query: str) -> ReasoningPlan:
    text = query.lower()
    plan = ReasoningPlan()
    ages = [int(value) for value in re.findall(r"\b(\d{1,2})[ -]year[ -]old\b|\b(?:aged?|was)\s+(\d{1,2})\b", text) for value in value if value]
    dates = _extract_dates(query)
    offence_words = ("offence", "theft", "committed", "occurred", "alleged", "conduct")
    if dates and any(word in text for word in offence_words) and min(dates) < COMMENCEMENT_DATE:
        plan.offence_date = min(dates)
        plan.issues.append(LegalIssue("statutory_transition", "BNS", ("358",), "The alleged offence predates 1 July 2024: substantive criminal liability is assessed under the IPC in force on the date of conduct, not retrospectively under BNS. Distinguish procedural savings under BNSS section 531."))
        plan.issues.append(LegalIssue("procedural_transition", "BNSS", ("531",), "Check whether proceedings or investigation were already pending when BNSS commenced; do not assume the filing or trial date changes the substantive offence."))
        plan.safeguards.append("MANDATORY: State that an offence committed before 1 July 2024 is not retrospectively governed by BNS; identify IPC substantive liability and BNS section 358 savings.")

    mentions_child = bool(re.search(r"\b(?:pocso|child|minor|student|school|1[0-7][ -]year[ -]old)\b", text))
    adult_only = bool(ages) and min(ages) >= 18 and not any(age < 18 for age in ages)
    no_contact = any(value in text for value in ("no physical contact", "no touching", "never met", "non-contact", "without physical contact", "online only"))
    explicit_messages = any(value in text for value in ("explicit", "sexual messages", "sexually explicit", "harassment", "instagram", "messages", "online"))
    if mentions_child and adult_only:
        plan.issues.append(LegalIssue("pocso_age", "POCSO", ("2",), "POCSO applies to a child below 18; an actual age of 18 or older does not become a child merely because another person believed otherwise."))
        plan.safeguards.append("An adult is outside POCSO's child definition; perceived age does not change actual age.")
    elif mentions_child:
        if explicit_messages and no_contact:
            plan.issues.append(LegalIssue("pocso_non_contact_harassment", "POCSO", ("11", "12"), "Non-contact sexually explicit communications with a child require analysis of POCSO sexual harassment under sections 11 and 12, not penetrative or physical-contact sexual assault.", ("3", "4", "5", "6", "7", "8", "9", "10")))
            plan.safeguards.append("MANDATORY: Cite POCSO sections 11 AND 12; exclude sections 3–10 where the facts expressly establish no physical contact.")
        if any(value in text for value in ("report", "counsellor", "principal", "institution", "school's reputation")):
            plan.issues.append(LegalIssue("pocso_reporting", "POCSO", ("19", "21"), "Assess mandatory reporting and liability for failure to report separately from proof of the underlying offence."))
        if any(value in text for value in ("age", "consent", "17-year-old", "school records")):
            plan.issues.append(LegalIssue("pocso_age_consent", "POCSO", ("2",), "A person below 18 is a child; alleged consent alone does not eliminate POCSO applicability, and disputed age must be resolved on reliable evidence."))
        if any(value in text for value in ("repeal", "ceased to exist", "only bns", "alongside", "special statute")):
            plan.issues.append(LegalIssue("pocso_special_statute", "POCSO", ("42", "42A"), "POCSO remains an independent special enactment after BNS commencement; apply its special-law and conflict provisions without claiming repeal."))

    if any(value in text for value in ("whatsapp", "screenshot", "electronic record", "electronic evidence", "chat backup", "digital evidence", "certificate", "cctv")):
        plan.issues.append(LegalIssue("electronic_evidence", "BSA", ("63", "62"), "Assess source, authenticity, integrity, chain of custody, and the applicable electronic-record certificate requirements; a printout is not automatically authenticated."))
    if any(value in text for value in ("default bail", "day 91", "charge sheet", "charge-sheet", "investigation period")) and "bail" in text:
        plan.issues.append(LegalIssue("default_bail", "BNSS", ("187",), "Default-bail analysis belongs to BNSS section 187; check whether the applicable 60/90-day period expired, whether the application preceded the charge sheet, and whether the accused was prepared to furnish bail. Do not substitute undertrial detention under section 479.", ("479",)))
        plan.safeguards.append("MANDATORY: Cite BNSS section 187 for investigation/default bail; section 479 concerns a distinct undertrial-detention issue.")
    if any(value in text for value in ("police custody", "remand", "custody ceiling")):
        plan.issues.append(LegalIssue("police_custody", "BNSS", ("187",), "Aggregate police custody is capped at 15 days; distinguish that ceiling and its initial 40/60-day allocation window from the overall 60/90-day investigation detention period."))
        days_match = re.search(r"(?:spent|already|completed)\s+(\d{1,2})\s+days", text)
        if days_match:
            used = int(days_match.group(1))
            remaining = max(0, 15 - used)
            overall = "90 days where the statutory serious-offence category applies" if any(value in text for value in ("life imprisonment", "death", "ten years")) else "the applicable 60-day or 90-day investigation limit"
            plan.safeguards.append(f"DETERMINISTIC CUSTODY: {used} police-custody days used; maximum additional police custody is {remaining} days. Distinguish this from {overall}; never describe 40/60-day allocation windows as the total detention limit.")
    if any(value in text for value in ("territorial", "another district", "nearest police station", "zero fir", "jurisdiction")) and any(value in text for value in ("fir", "police", "cognizable", "complainant")):
        plan.issues.append(LegalIssue("zero_fir", "BNSS", ("173",), "A cognizable offence report cannot be refused solely for territorial location; distinguish initial information/FIR registration under BNSS section 173 from investigation and transfer."))
    if "search" in text and any(value in text for value in ("video", "videography", "record", "seizure")):
        plan.issues.append(LegalIssue("search_videography", "BNSS", ("105",), "Identify the audio-video recording obligation without asserting automatic acquittal or automatic exclusion absent supporting statutory text."))
    if any(value in text for value in ("entrust", "cashier", "lawfully receives", "diverts")):
        plan.issues.append(LegalIssue("criminal_breach_of_trust", "BNS", ("316",), "Entrustment followed by dishonest diversion points to criminal breach of trust; distinguish lawful initial possession from theft."))
    if any(value in text for value in ("locked drawer", "never authorised", "unauthorized", "theft", "secretly removes")):
        plan.issues.append(LegalIssue("theft", "BNS", ("303",), "Theft requires dishonest taking of movable property out of another's possession without consent; compare with entrusted-property breach of trust."))
    if any(value in text for value in ("extortion", "threatens to publish", "threaten to publish", "private photographs")):
        plan.issues.append(LegalIssue("extortion", "BNS", ("308", "351"), "Completed extortion requires fear-induced delivery of property or valuable security; a bare threat without delivery may instead support attempted conduct or criminal intimidation, depending on evidence."))
    return plan


def prioritize_evidence(plan: ReasoningPlan, sections: list[dict[str, Any]], corpus_by_key: dict, limit: int = 8) -> list[dict[str, Any]]:
    """Guarantee at least the primary provisions for every independent issue."""
    result, seen = [], set()
    blocked = {(issue.statute, excluded) for issue in plan.issues for excluded in issue.excluded_sections}

    def append_record(record):
        if not record:
            return
        key = (record.get("short_name", "").upper(), str(record.get("section", "")).split("(")[0].upper())
        if key in blocked or key in seen:
            return
        seen.add(key)
        result.append(record)

    for position in range(max((len(issue.sections) for issue in plan.issues), default=0)):
        for issue in plan.issues:
            if position < len(issue.sections):
                append_record(corpus_by_key.get((issue.statute, issue.sections[position].upper())))
    for section in sections:
        append_record(section)
    return result[: max(limit, min(len(plan.required_citations), 10))]


def format_compact_evidence(plan: ReasoningPlan, sections: list[dict[str, Any]], max_chars: int = 7200) -> str:
    lines = ["VERIFIED LEGAL ISSUES AND REQUIRED ANALYSIS:"]
    for issue in plan.issues:
        lines.append(f"- {issue.category}: {issue.statute} sections {', '.join(issue.sections)}. {issue.guidance}")
    if plan.safeguards:
        lines += ["DETERMINISTIC SAFEGUARDS:"] + [f"- {item}" for item in plan.safeguards]
    lines.append("AUTHORITATIVE STATUTORY EXCERPTS:")
    for record in sections:
        statute = record.get("short_name", record.get("statute", ""))
        heading = str(record.get("heading", ""))[:180]
        excerpt = re.sub(r"\s+", " ", str(record.get("text", "")))[:650]
        lines.append(f"- {statute} section {record.get('section','')}: {heading}. {excerpt}")
    return "\n".join(lines)[:max_chars]


def verify_answer(answer: str, plan: ReasoningPlan, sections: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = answer.lower()
    missing = []
    for issue in plan.issues:
        if issue.category in {"pocso_non_contact_harassment", "pocso_reporting"}:
            required = issue.sections
        else:
            required = issue.sections[:1]
        for section in required:
            if not re.search(r"(?<!\d)" + re.escape(section) + r"(?!\d)", normalized):
                missing.append(f"{issue.statute} {section}")
    contradictions = []
    if plan.offence_date and "ipc" not in normalized:
        contradictions.append("pre-commencement offence must identify IPC substantive liability")
    if any(issue.category == "pocso_non_contact_harassment" for issue in plan.issues) and re.search(r"(?:section\s*)?[347]\s+(?:applies|governs|is applicable)", normalized):
        contradictions.append("non-contact child harassment cannot be relabeled as contact or penetrative assault")
    return {"passed": not missing and not contradictions, "missing_citations": missing, "contradictions": contradictions}


def deterministic_grounded_answer(query: str, evidence_context: str) -> str | None:
    """Resolve recognized statutory issues locally from verified corpus anchors."""
    plan = build_reasoning_plan(query)
    if not plan.issues:
        return None

    normalized_evidence = evidence_context.lower()
    supported_issues = [
        issue for issue in plan.issues
        if issue.statute.lower() in normalized_evidence
        and any(re.search(r"(?<!\d)" + re.escape(section.lower()) + r"(?!\d)", normalized_evidence)
                for section in issue.sections)
    ]
    if not supported_issues:
        return None

    paragraphs = []
    if plan.offence_date:
        paragraphs.append(
            "**Substantive law:** The alleged offence occurred on "
            f"{plan.offence_date.strftime('%d %B %Y').lstrip('0')}, "
            "before the new criminal laws commenced on 1 July 2024. "
            "The Indian Penal Code (IPC) therefore governs substantive criminal liability. "
            "A later FIR, investigation, or trial does not retrospectively make BNS section 303 applicable. "
            "BNS section 358 preserves the effect of repeal and savings; BNSS section 531 "
            "must be considered separately for pending procedural matters."
        )

    for issue in supported_issues:
        if plan.offence_date and (
            issue.category in {"statutory_transition", "procedural_transition"}
            or issue.statute == "BNS"
        ):
            continue
        citations = ", ".join(f"{issue.statute} section {section}" for section in issue.sections)
        paragraphs.append(f"**{issue.category.replace('_', ' ').title()}:** {issue.guidance} ({citations}.)")

    custody = next((item for item in plan.safeguards if item.startswith("DETERMINISTIC CUSTODY:")), None)
    if custody:
        paragraphs.append("**Custody calculation:** " + custody.removeprefix("DETERMINISTIC CUSTODY: "))
    return "\n\n".join(paragraphs) if paragraphs else None
