"""Deterministic issue planning and citation guardrails for Indian legal RAG."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from retrieval.transition_context import COMMENCEMENT_DATE, analyze_transition

DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
DATE_CANDIDATE_RE = re.compile(
    r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b|"
    r"\b\d{4}-\d{2}-\d{2}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"
)
ELECTRONIC_FIR_EVENT_RE = re.compile(
    r"\b(?:"
    r"fir\b[^.\n]{0,80}\b(?:electronically|electronic|online)|"
    r"(?:electronically|online)\b[^.\n]{0,60}\b"
    r"(?:report(?:ed)?|submit(?:ted)?|lodg(?:ed)?|fil(?:e|ed)|register(?:ed)?)"
    r")\b",
    re.IGNORECASE,
)
SIGNATURE_EVENT_RE = re.compile(r"\b(?:signed|signing|signature)\b", re.IGNORECASE)


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
    procedure_start_date: date | None = None
    pending_before_commencement: bool | None = None
    procedure_regime: str = "UNKNOWN"
    evidence_regime: str = "UNKNOWN"

    @property
    def required_citations(self) -> list[tuple[str, str]]:
        return [(issue.statute, section) for issue in self.issues for section in issue.sections]

    @property
    def is_complex(self) -> bool:
        """Complex fact patterns require model synthesis rather than canned summaries."""
        return len(self.issues) >= 2 or len({issue.statute for issue in self.issues}) >= 2


def _extract_dates(query: str) -> list[date]:
    candidates = DATE_CANDIDATE_RE.findall(query)
    found = []
    for candidate in candidates:
        for pattern in DATE_FORMATS:
            try:
                found.append(datetime.strptime(candidate, pattern).date())
                break
            except ValueError:
                continue
    return found


def _nearest_event_date(query: str, event_pattern: re.Pattern[str]) -> date | None:
    """Return the date nearest a named event, preferring dates in its sentence."""
    dated_matches = []
    for match in DATE_CANDIDATE_RE.finditer(query):
        parsed = _extract_dates(match.group(0))
        if parsed:
            dated_matches.append((match, parsed[0]))
    if not dated_matches:
        return None

    for event in event_pattern.finditer(query):
        sentence_start = max(query.rfind(".", 0, event.start()), query.rfind("\n", 0, event.start())) + 1
        period_end = query.find(".", event.end())
        newline_end = query.find("\n", event.end())
        sentence_ends = [value for value in (period_end, newline_end) if value >= 0]
        sentence_end = min(sentence_ends) if sentence_ends else len(query)
        candidates = [
            item for item in dated_matches
            if sentence_start <= item[0].start() <= sentence_end
        ]
        if not candidates:
            candidates = [
                item for item in dated_matches
                if abs(item[0].start() - event.start()) <= 120
            ]
        if candidates:
            def distance(item: tuple[re.Match[str], date]) -> int:
                match = item[0]
                if match.end() < event.start():
                    return event.start() - match.end()
                if match.start() > event.end():
                    return match.start() - event.end()
                return 0

            return min(candidates, key=distance)[1]
    return None


def _electronic_fir_timing_guidance(query: str) -> str:
    report_date = _nearest_event_date(query, ELECTRONIC_FIR_EVENT_RE)
    signature_date = _nearest_event_date(query, SIGNATURE_EVENT_RE)
    if report_date is None or signature_date is None:
        return ""

    elapsed_days = (signature_date - report_date).days
    report_label = report_date.strftime("%d %B %Y").lstrip("0")
    signature_label = signature_date.strftime("%d %B %Y").lstrip("0")
    if 0 <= elapsed_days <= 3:
        day_label = "day" if elapsed_days == 1 else "days"
        return (
            f" On the stated dates, the signature on {signature_label} was {elapsed_days} "
            f"{day_label} after the electronic report on {report_label}, so section 173's "
            "three-day timing requirement was satisfied."
        )
    if elapsed_days > 3:
        return (
            f" On the stated dates, the signature on {signature_label} came more than three "
            f"days after the electronic report on {report_label}, so it did not satisfy section "
            "173's three-day timing requirement."
        )
    return ""


@lru_cache(maxsize=1024)
def build_reasoning_plan(query: str) -> ReasoningPlan:
    text = query.lower()
    timeline = analyze_transition(query)
    plan = ReasoningPlan(
        offence_date=timeline.offence_date,
        procedure_start_date=timeline.procedure_start_date,
        pending_before_commencement=timeline.pending_before_commencement,
        procedure_regime=timeline.procedure_regime,
        evidence_regime=timeline.evidence_regime,
    )
    ages = [int(value) for value in re.findall(r"\b(\d{1,2})[ -]year[ -]old\b|\b(?:aged?|was)\s+(\d{1,2})\b", text) for value in value if value]
    is_pre_commencement_offence = bool(plan.offence_date and plan.offence_date < COMMENCEMENT_DATE)
    if is_pre_commencement_offence:
        plan.issues.append(LegalIssue(
            "statutory_transition", "BNS", ("358",),
            "The alleged offence predates 1 July 2024. Apply the IPC substantive offence in force on the conduct date; BNS section 358 preserves pre-repeal liability and does not make the corresponding BNS offence retrospective.",
        ))
        if "theft" in text:
            plan.issues.append(LegalIssue(
                "legacy_theft", "IPC", ("378", "379"),
                "IPC section 378 supplies the definition of theft and IPC section 379 supplies its punishment for this pre-commencement allegation. Do not substitute the corresponding BNS theft provision.",
            ))
        plan.issues.append(LegalIssue(
            "procedural_transition", "BNSS", ("531",),
            "Decide procedure independently: matters pending immediately before 1 July 2024 continue under CrPC; a later-started matter is not moved to CrPC solely because the alleged offence predates commencement.",
        ))
        if plan.procedure_regime == "CRPC":
            plan.safeguards.append(
                "TRANSITION PROCEDURE: The relevant matter was pending before commencement; apply saved CrPC procedure under BNSS section 531(2)(a)."
            )
        elif plan.procedure_regime == "BNSS":
            plan.safeguards.append(
                "TRANSITION PROCEDURE: The relevant matter began on or after commencement; apply BNSS procedure, while retaining IPC substantive liability for the earlier conduct."
            )
        else:
            plan.safeguards.append(
                "TRANSITION PROCEDURE: The facts do not establish whether an investigation or proceeding was pending immediately before 1 July 2024. State both branches under BNSS section 531(2)(a); do not choose one without a procedural start fact."
            )
        plan.safeguards.append(
            "MANDATORY: State that a pre-1 July 2024 offence is not retrospectively governed by BNS; cite IPC sections 378 and 379 for theft and BNS section 358 for savings."
        )

    mentions_child = bool(re.search(r"\b(?:pocso|child|minor|student|school|1[0-7][ -]year[ -]old)\b", text))
    adult_only = bool(ages) and min(ages) >= 18 and not any(age < 18 for age in ages)
    no_contact = any(value in text for value in (
        "no physical contact", "no touching", "never met", "non-contact",
        "without physical contact", "online only", "never touched", "did not touch",
        "didn't touch", "without touching", "no physical touch", "absence of physical contact",
    ))
    explicit_messages = any(value in text for value in ("explicit", "sexual messages", "sexually explicit", "harassment", "instagram", "messages", "online"))
    if mentions_child and adult_only:
        plan.issues.append(LegalIssue("pocso_age", "POCSO", ("2",), "POCSO applies to a child below 18; an actual age of 18 or older does not become a child merely because another person believed otherwise."))
        plan.safeguards.append("An adult is outside POCSO's child definition; perceived age does not change actual age.")
    elif mentions_child:
        if explicit_messages and no_contact:
            plan.issues.append(LegalIssue("pocso_non_contact_harassment", "POCSO", ("11", "12"), "Non-contact sexually explicit communications with a child require analysis of POCSO sexual harassment under sections 11 and 12, not penetrative or physical-contact sexual assault.", ("3", "4", "5", "6", "7", "8", "9", "10")))
            plan.safeguards.append("MANDATORY: Cite POCSO sections 11 AND 12; exclude sections 3–10 where the facts expressly establish no physical contact.")
        if any(value in text for value in ("report", "teacher", "counsellor", "principal", "institution", "school's reputation")):
            plan.issues.append(LegalIssue(
                "pocso_reporting", "POCSO", ("19", "21"),
                "Assess the reporting duty under section 19 and possible liability under section 21 separately from proof of the underlying offence. Do not call delayed reporting automatically punishable: section 21 addresses failure to report or record, so the effect of a later report depends on the facts and legal interpretation.",
            ))
        if any(value in text for value in ("age", "consent", "17-year-old", "school records")):
            plan.issues.append(LegalIssue(
                "pocso_age_consent", "POCSO", ("2",),
                "A person below 18 is a child. Alleged consent does not by itself remove POCSO applicability, but each charged offence—including sexual intent under section 11—must still be proved on admissible evidence; disputed age requires reliable proof.",
            ))
        if any(value in text for value in ("repeal", "ceased to exist", "only bns", "alongside", "special statute")):
            plan.issues.append(LegalIssue("pocso_special_statute", "POCSO", ("42", "42A"), "POCSO remains an independent special enactment after BNS commencement; apply its special-law and conflict provisions without claiming repeal."))

    has_electronic_evidence = any(value in text for value in (
        "whatsapp", "screenshot", "electronic record", "electronic evidence",
        "chat backup", "digital evidence", "certificate", "cctv", "laptop files",
    ))
    if has_electronic_evidence:
        if is_pre_commencement_offence or plan.evidence_regime == "IEA":
            if plan.evidence_regime == "BSA":
                evidence_transition_guidance = (
                    "BSA section 170 governs the evidence-law transition. Because the relevant "
                    "matter began after commencement, BSA applies; the earlier offence date does "
                    "not preserve the Indian Evidence Act for that later-started matter."
                )
            elif plan.evidence_regime == "IEA":
                evidence_transition_guidance = (
                    "BSA section 170 saves the Indian Evidence Act for this relevant matter "
                    "because it was pending immediately before commencement."
                )
            else:
                evidence_transition_guidance = (
                    "BSA section 170 makes pendency immediately before commencement decisive: "
                    "the Indian Evidence Act governs a saved pending matter, while BSA governs "
                    "a matter begun on or after commencement. The offence date alone does not "
                    "select the evidence statute."
                )
            plan.issues.append(LegalIssue(
                "evidence_transition", "BSA", ("170",),
                evidence_transition_guidance,
            ))
        if plan.evidence_regime == "IEA":
            plan.issues.append(LegalIssue(
                "electronic_evidence_legacy", "IEA", ("65B", "65A"),
                "For a saved Indian Evidence Act matter, electronic computer outputs are proved under IEA sections 65A and 65B. State the statutory conditions and certificate requirement actually supported by the excerpt; do not attribute every forensic concern to section 65B.",
            ))
        elif plan.evidence_regime == "BSA":
            plan.issues.append(LegalIssue(
                "electronic_evidence_current", "BSA", ("63", "62"),
                "Under BSA, section 62 directs proof of electronic-record contents to section 63, which governs computer-output conditions and certification. Authenticity, integrity, and evidentiary weight remain separate questions rather than additional conditions stated in section 63.",
            ))
        elif is_pre_commencement_offence:
            plan.issues.append(LegalIssue(
                "electronic_evidence_legacy_branch", "IEA", ("65B", "65A"),
                "If the relevant matter was pending immediately before commencement, IEA sections 65A and 65B govern electronic computer outputs.",
            ))
            plan.issues.append(LegalIssue(
                "electronic_evidence_current_branch", "BSA", ("63", "62"),
                "If the relevant matter began on or after commencement, BSA sections 62 and 63 govern proof of electronic records and computer outputs.",
            ))
            plan.safeguards.append(
                "EVIDENCE TRANSITION: The offence date alone does not select IEA or BSA. Apply BSA section 170 to the relevant pending matter and state both branches if pendency is unknown."
            )
        else:
            plan.issues.append(LegalIssue(
                "electronic_evidence_current", "BSA", ("63", "62"),
                "BSA sections 62 and 63 govern proof of electronic records and computer outputs, including section 63 conditions and certification. Distinguish express statutory conditions from separate forensic-weight questions.",
            ))

    has_electronic_fir = any(value in text for value in (
        "electronic fir", "e-fir", "e fir", "fir electronically", "fir is registered electronically",
        "register the fir electronically", "register an fir electronically", "online fir",
    )) or ("fir" in text and any(value in text for value in ("electronically", "electronic registration", "online registration")))
    if has_electronic_fir:
        if plan.procedure_regime == "CRPC":
            plan.issues.append(LegalIssue(
                "legacy_fir_registration", "CRPC", ("154",),
                "The saved CrPC section 154 governs recording cognizable information. Do not import BNSS section 173's express electronic-communication and three-day signature rules into a saved CrPC matter.",
            ))
        else:
            qualifier = "" if plan.procedure_regime == "BNSS" else "If BNSS governs the later-started matter, "
            timing_guidance = _electronic_fir_timing_guidance(query) if plan.procedure_regime == "BNSS" else ""
            plan.issues.append(LegalIssue(
                "electronic_fir_registration", "BNSS", ("173",),
                qualifier + "BNSS section 173 covers cognizable information irrespective of area and permits electronic communication, subject to the statutory signature-within-three-days requirement. The registration question is separate from later investigation and proof." + timing_guidance,
            ))
    if any(value in text for value in ("default bail", "day 91", "charge sheet", "charge-sheet", "investigation period")) and "bail" in text:
        if plan.procedure_regime == "CRPC":
            plan.issues.append(LegalIssue(
                "legacy_default_bail", "CRPC", ("167",),
                "For a saved investigation, default-bail analysis belongs to CrPC section 167. Check expiry of the applicable period, the timing of the application and charge sheet, and readiness to furnish bail.",
            ))
        else:
            plan.issues.append(LegalIssue("default_bail", "BNSS", ("187",), "Default-bail analysis belongs to BNSS section 187; check whether the applicable 60/90-day period expired, whether the application preceded the charge sheet, and whether the accused was prepared to furnish bail. Do not substitute undertrial detention under section 479.", ("479",)))
            plan.safeguards.append("MANDATORY: Cite BNSS section 187 for investigation/default bail; section 479 concerns a distinct undertrial-detention issue.")
    if any(value in text for value in ("police custody", "remand", "custody ceiling")):
        ordinary_legacy_theft = is_pre_commencement_offence and any(
            issue.category == "legacy_theft" for issue in plan.issues
        )
        if plan.procedure_regime == "CRPC":
            plan.issues.append(LegalIssue(
                "legacy_police_custody", "CRPC", ("167",),
                "A saved pre-commencement investigation is governed by CrPC section 167, not BNSS section 187. Do not assume unused days are automatically available without considering the applicable remand stage and judicial authorisation.",
            ))
        elif plan.procedure_regime == "BNSS" or not is_pre_commencement_offence:
            if ordinary_legacy_theft:
                custody_guidance = (
                    "The stated IPC section 379 theft allegation carries a maximum punishment "
                    "of three years. It therefore falls within BNSS section 187's sixty-day "
                    "investigation category, making the police-custody allocation window the "
                    "initial forty days. Police custody remains capped at fifteen days in the "
                    "whole, usable wholly or in parts, and every period requires Magistrate "
                    "authorisation."
                )
            else:
                custody_guidance = (
                    "BNSS section 187 caps police custody at fifteen days in the whole, usable "
                    "wholly or in parts within the applicable initial forty- or sixty-day "
                    "allocation window. The overall sixty- or ninety-day investigation-detention "
                    "limit is distinct, and every period requires Magistrate authorisation."
                )
            plan.issues.append(LegalIssue(
                "police_custody", "BNSS", ("187",),
                custody_guidance,
            ))
        else:
            plan.issues.append(LegalIssue(
                "police_custody_current_branch", "BNSS", ("187",),
                "If BNSS governs, section 187 supplies the fifteen-day aggregate police-custody ceiling and the initial forty- or sixty-day allocation window.",
            ))
            plan.issues.append(LegalIssue(
                "police_custody_legacy_branch", "CRPC", ("167",),
                "If the investigation was pending before commencement, CrPC section 167 governs custody; do not apply BNSS section 187 merely from the remand date.",
            ))
        days_match = re.search(r"(?:spent|already|completed)\s+(\d{1,2})\s+days", text)
        if days_match:
            used = int(days_match.group(1))
            remaining = max(0, 15 - used)
            remaining_label = "day" if remaining == 1 else "days"
            if ordinary_legacy_theft:
                allocation_window = "initial 40-day police-custody allocation window"
                overall = "60-day investigation-detention limit"
            elif any(value in text for value in ("life imprisonment", "death", "ten years")):
                allocation_window = "initial 60-day police-custody allocation window"
                overall = "investigation-detention limit of 90 days"
            else:
                allocation_window = "applicable initial 40/60-day police-custody allocation window"
                overall = "applicable investigation-detention limit of 60 or 90 days"
            if plan.procedure_regime == "BNSS":
                plan.safeguards.append(
                    f"DETERMINISTIC CUSTODY: If the earlier {used} police-custody days were validly authorised under BNSS section 187, no more than {remaining} aggregate {remaining_label} remain. This arithmetic is not an authorisation; the Magistrate and the {allocation_window} still control. The separate {overall} governs the investigation-detention period."
                )
            elif plan.procedure_regime == "CRPC":
                plan.safeguards.append(
                    f"DETERMINISTIC CUSTODY: CrPC section 167, not BNSS section 187, governs. The fifteen-day statutory aggregate leaves at most {remaining} unused {remaining_label}, but do not say those days are automatically available; remand timing and valid judicial authorisation require separate analysis."
                )
            else:
                plan.safeguards.append(
                    f"DETERMINISTIC CUSTODY: Do not state that {remaining} {remaining_label} remain unconditionally. If BNSS governs and {used} days were validly authorised, no more than {remaining} aggregate {remaining_label} remain under section 187, subject to its timing window and Magistrate authorisation; if CrPC is saved, section 167 requires separate remand analysis. Distinguish either custody analysis from {overall}."
                )
    if any(value in text for value in ("territorial", "another district", "nearest police station", "zero fir", "jurisdiction")) and any(value in text for value in ("fir", "police", "cognizable", "complainant")):
        if plan.procedure_regime == "CRPC":
            plan.issues.append(LegalIssue(
                "legacy_territorial_fir", "CRPC", ("154",),
                "CrPC section 154 governs the saved matter. Do not cite BNSS section 173's express 'irrespective of area' language as though it applied; any broader Zero-FIR conclusion needs authority applicable to the CrPC regime.",
            ))
        else:
            qualifier = "Under BNSS, " if plan.procedure_regime == "BNSS" else "If BNSS governs, "
            plan.issues.append(LegalIssue(
                "zero_fir", "BNSS", ("173",),
                qualifier + "cognizable information cannot be refused solely because the offence occurred outside the station's area. Registration under section 173 is separate from later investigation and transfer.",
            ))
    if "search" in text and any(value in text for value in ("video", "videography", "record", "seizure")):
        if plan.procedure_regime == "CRPC":
            plan.issues.append(LegalIssue(
                "legacy_search", "CRPC", ("100", "165"),
                "For a saved CrPC investigation, assess the search under CrPC sections 100 and 165; BNSS section 105's audio-video duty does not apply merely because the search is discussed after commencement.",
            ))
        else:
            qualifier = "Under BNSS, " if plan.procedure_regime == "BNSS" else "If BNSS governs, "
            plan.issues.append(LegalIssue(
                "search_videography", "BNSS", ("105",),
                qualifier + "section 105 requires audio-video recording of the search-and-seizure process and forwarding of the recording. The supplied text does not prescribe automatic acquittal or automatic exclusion for breach. Any further consequence requires separate authority and fact-specific analysis.",
            ))
    if any(value in text for value in ("entrust", "cashier", "lawfully receives", "diverts")):
        plan.issues.append(LegalIssue("criminal_breach_of_trust", "BNS", ("316",), "Entrustment followed by dishonest diversion points to criminal breach of trust; distinguish lawful initial possession from theft."))
    if not is_pre_commencement_offence and any(value in text for value in ("locked drawer", "never authorised", "unauthorized", "theft", "secretly removes")):
        plan.issues.append(LegalIssue("theft", "BNS", ("303",), "Theft requires dishonest taking of movable property out of another's possession without consent; compare with entrusted-property breach of trust."))
    if any(value in text for value in (
        "extortion", "threatens to publish", "threaten to publish", "threatening to publish",
        "threatened to publish", "publish edited intimate", "publish intimate images",
        "leak intimate images", "private photographs", "threat to publish",
    )):
        plan.issues.append(LegalIssue(
            "extortion", "BNS", ("308", "351"),
            "Completed extortion under section 308 requires fear-induced delivery of property or valuable security. A demand that the child merely meet the accused does not establish that element; the threat may instead require analysis as criminal intimidation under section 351, subject to proof of its elements.",
        ))
    if any(value in text for value in (
        "conclusively establish guilt", "conclusively prove guilt", "proof of guilt",
        "establish guilt", "prove the allegations", "facts alone", "presumption of innocence",
    )):
        plan.safeguards.append(
            "MANDATORY: Distinguish an allegation and a prima facie statutory assessment from proof at trial; identity, authenticity, intent, age, and any disputed facts require admissible evidence. Do not pronounce guilt from the narrative alone."
        )
    if any(value in text for value in (
        "establish innocence", "prove innocence", "automatic acquittal", "automatically acquit",
        "procedural defects", "evidentiary defects", "defects mean innocence",
    )):
        plan.safeguards.append(
            "MANDATORY DEFECT CONSEQUENCE: Do not say defects prove innocence, and do not invoke what legal systems 'typically' do. Identify the specific breached provision and any consequence stated in retrieved authority. If no automatic remedy is stated, say the supplied authority does not establish one and that the remaining consequence requires separate authority and fact-specific adjudication."
        )
    return plan


def prioritize_evidence(plan: ReasoningPlan, sections: list[dict[str, Any]], corpus_by_key: dict, limit: int = 8) -> list[dict[str, Any]]:
    """Guarantee at least the primary provisions for every independent issue."""
    result, seen = [], set()
    blocked = {(issue.statute, excluded) for issue in plan.issues for excluded in issue.excluded_sections}
    if plan.offence_date and plan.offence_date < COMMENCEMENT_DATE:
        blocked.add(("BNS", "303"))
    if plan.procedure_regime == "CRPC":
        blocked.update({("BNSS", section) for section in ("35", "105", "173", "187")})
    if plan.evidence_regime == "IEA":
        blocked.update({("BSA", section) for section in ("61", "62", "63")})

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
    # Complex transition matters can legitimately require old-law, new-law, and
    # savings provisions at once.  Do not drop the second half of a paired citation
    # (for example IPC 379 or BSA 62) merely because the UI requested top_k=10.
    return result[: max(limit, min(len(plan.required_citations), 16))]


def format_compact_evidence(plan: ReasoningPlan, sections: list[dict[str, Any]], max_chars: int = 18000) -> str:
    lines = ["VERIFIED LEGAL ISSUES AND REQUIRED ANALYSIS:"]
    for issue in plan.issues:
        lines.append(f"- {issue.category}: {issue.statute} sections {', '.join(issue.sections)}. {issue.guidance}")
    if plan.safeguards:
        lines += ["DETERMINISTIC SAFEGUARDS:"] + [f"- {item}" for item in plan.safeguards]
    lines.append("AUTHORITATIVE STATUTORY MATERIAL:")
    for record in sections:
        statute = record.get("short_name", record.get("statute", ""))
        heading = str(record.get("heading", ""))[:180]
        excerpt = re.sub(r"\s+", " ", str(record.get("text", "")))[:600]
        lines.append(f"- {statute} section {record.get('section','')}: {heading}. {excerpt}")
    return "\n".join(lines)[:max_chars]


def verified_evidence_material(evidence_context: str) -> str:
    """Remove planner instructions before checking whether a citation was retrieved."""
    for marker in ("AUTHORITATIVE STATUTORY MATERIAL:", "AUTHORITATIVE STATUTORY EXCERPTS:"):
        if marker in evidence_context:
            return evidence_context.split(marker, 1)[-1]
    return evidence_context


def citation_is_grounded(statute: str, section: str, evidence_context: str) -> bool:
    excerpt = verified_evidence_material(evidence_context)
    pattern = (
        r"\b" + re.escape(statute) + r"\b[^\n]{0,80}\bsections?\s*"
        + re.escape(section) + r"(?!\d)"
    )
    return bool(re.search(pattern, excerpt, re.IGNORECASE))


def verify_answer(answer: str, plan: ReasoningPlan, sections: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = answer.lower()
    missing = []
    require_all_categories = {
        "pocso_non_contact_harassment", "pocso_reporting", "legacy_theft",
        "electronic_evidence_current", "electronic_evidence_current_branch",
        "electronic_evidence_legacy", "electronic_evidence_legacy_branch",
    }
    for issue in plan.issues:
        if issue.category in require_all_categories:
            required = issue.sections
        else:
            required = issue.sections[:1]
        for section in required:
            if not re.search(r"(?<!\d)" + re.escape(section) + r"(?!\d)", normalized):
                missing.append(f"{issue.statute} {section}")
    contradictions = []
    if plan.offence_date and plan.offence_date < COMMENCEMENT_DATE and "ipc" not in normalized:
        contradictions.append("pre-commencement offence must identify IPC substantive liability")
    if plan.offence_date and plan.offence_date < COMMENCEMENT_DATE and re.search(
        r"bns\s+(?:section\s+)?303[^.\n]{0,90}\b(?:applies|governs|applicable|charge|prosecution)",
        normalized,
    ):
        contradictions.append("BNS section 303 cannot govern a pre-commencement theft allegation")
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
    pre_commencement = bool(plan.offence_date and plan.offence_date < COMMENCEMENT_DATE)
    if pre_commencement:
        theft_citations = "IPC sections 378 and 379; " if any(
            issue.category == "legacy_theft" for issue in supported_issues
        ) else ""
        paragraphs.append(
            "**1. Substantive criminal law:** The alleged conduct occurred on "
            f"{plan.offence_date.strftime('%d %B %Y').lstrip('0')}, before commencement on "
            "1 July 2024. The Indian Penal Code (IPC) therefore governs substantive criminal "
            "liability; a later "
            "FIR, investigation, or trial does not retrospectively replace that offence with "
            f"its BNS counterpart ({theft_citations}BNS section 358)."
        )

        if plan.procedure_regime == "BNSS":
            procedure_text = (
                "The stated investigation/proceeding began on or after 1 July 2024, so BNSS "
                "governs procedure while IPC continues to govern the earlier substantive offence."
            )
        elif plan.procedure_regime == "CRPC":
            procedure_text = (
                "The relevant investigation/proceeding was pending immediately before 1 July "
                "2024 and therefore continues under CrPC."
            )
        else:
            procedure_text = (
                "The facts do not say whether the relevant matter was pending immediately before "
                "1 July 2024. If it was pending, CrPC continues; if it began afterward, BNSS applies."
            )
        paragraphs.append(f"**2. Procedural transition:** {procedure_text} (BNSS section 531.)")

    label_map = {
        "electronic_fir_registration": "Electronic FIR",
        "legacy_fir_registration": "FIR registration",
        "zero_fir": "Territorial objection / Zero FIR",
        "legacy_territorial_fir": "Territorial objection / FIR",
        "police_custody": "Police custody",
        "legacy_police_custody": "Police custody",
        "police_custody_current_branch": "Police custody — BNSS branch",
        "police_custody_legacy_branch": "Police custody — CrPC branch",
        "search_videography": "Search videography",
        "legacy_search": "Search procedure",
        "evidence_transition": "Evidence-law transition",
        "electronic_evidence_current": "Electronic records",
        "electronic_evidence_current_branch": "Electronic records — BSA branch",
        "electronic_evidence_legacy": "Electronic records",
        "electronic_evidence_legacy_branch": "Electronic records — IEA branch",
    }
    skip_categories = {"statutory_transition", "procedural_transition", "legacy_theft"}
    section_number = 3 if pre_commencement else 1
    emitted = set()
    for issue in supported_issues:
        if issue.category in skip_categories:
            continue
        key = (issue.category, issue.statute, issue.sections)
        if key in emitted:
            continue
        emitted.add(key)
        citations = ", ".join(f"{issue.statute} section {section}" for section in issue.sections)
        label = label_map.get(issue.category, issue.category.replace("_", " ").title())
        paragraphs.append(f"**{section_number}. {label}:** {issue.guidance} ({citations}.)")
        section_number += 1

    custody = next((item for item in plan.safeguards if item.startswith("DETERMINISTIC CUSTODY:")), None)
    if custody:
        paragraphs.append("**Custody calculation:** " + custody.removeprefix("DETERMINISTIC CUSTODY: "))
    if any(item.startswith("MANDATORY DEFECT CONSEQUENCE:") for item in plan.safeguards):
        paragraphs.append(
            "**Procedural and evidentiary defects:** The cited provisions do not state that the "
            "identified defects themselves establish innocence or require automatic acquittal. "
            "Any exclusion, prejudice, weight, or other remedy must be tied to applicable authority "
            "and the case facts; the available statutory excerpts alone do not establish a universal consequence."
        )
    return "\n\n".join(paragraphs) if paragraphs else None
