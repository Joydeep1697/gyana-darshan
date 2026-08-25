"""Present only unique statutory authorities actually cited in the final answer."""

from __future__ import annotations

import re
from typing import Any


STATUTE_PATTERNS = {
    "BNSS": r"(?:BNSS|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita)",
    "BNS": r"(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)",
    "BSA": r"(?:BSA|Bharatiya\s+Sakshya\s+Adhiniyam)",
    "POCSO": r"(?:POCSO|Protection\s+of\s+Children\s+from\s+Sexual\s+Offences\s+Act)",
    "CRPC": r"(?:CrPC|Code\s+of\s+Criminal\s+Procedure)",
    "IPC": r"(?:IPC|Indian\s+Penal\s+Code)",
    "IEA": r"(?:IEA|Indian\s+Evidence\s+Act)",
}

_CITATION_PATTERNS = {
    code: re.compile(
        rf"\b{pattern}\b\s*(?:,\s*\d{{4}})?\s*"
        rf"(?:sections?|secs?\.?|§)\s*"
        rf"([0-9][0-9A-Za-z()]*(?:\s*(?:,|and|&|to|[-–])\s*[0-9][0-9A-Za-z()]*)*)",
        re.IGNORECASE,
    )
    for code, pattern in STATUTE_PATTERNS.items()
}

_POSTFIX_CITATION_PATTERNS = {
    code: re.compile(
        rf"(?:sections?|secs?\.?|§)\s*"
        rf"([0-9][0-9A-Za-z()]*(?:\s*(?:,|and|&|to|[-–])\s*[0-9][0-9A-Za-z()]*)*)"
        rf"\s+of\s+(?:the\s+)?{pattern}\b",
        re.IGNORECASE,
    )
    for code, pattern in STATUTE_PATTERNS.items()
}


def _section_root(value: Any) -> str:
    match = re.match(r"\s*(\d+[A-Za-z]*)", str(value or ""), re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _statute_code(record: dict[str, Any]) -> str:
    short = str(record.get("short_name", "")).upper()
    if short in STATUTE_PATTERNS:
        return short
    statute = str(record.get("statute", ""))
    for code, pattern in STATUTE_PATTERNS.items():
        if re.search(rf"\b{pattern}\b", statute, re.IGNORECASE):
            return code
    return short or "STATUTE"


def _expand_sections(group: str) -> list[str]:
    values = [_section_root(value) for value in re.findall(r"\d+[A-Za-z]*(?:\(\d+\))?", group)]
    values = [value for value in values if value]
    if len(values) == 2 and re.search(r"\bto\b|[-–]", group, re.IGNORECASE):
        if values[0].isdigit() and values[1].isdigit():
            start, end = int(values[0]), int(values[1])
            if 0 <= end - start <= 10:
                return [str(number) for number in range(start, end + 1)]
    return list(dict.fromkeys(values))


def extract_citation_keys(answer: str) -> list[tuple[str, str]]:
    """Extract ordered statute-section pairs, including plural and range citations."""
    found: list[tuple[int, str, str]] = []
    for patterns in (_CITATION_PATTERNS, _POSTFIX_CITATION_PATTERNS):
        for code, pattern in patterns.items():
            for match in pattern.finditer(answer):
                for section in _expand_sections(match.group(1)):
                    found.append((match.start(), code, section))
    found.sort(key=lambda item: item[0])
    return list(dict.fromkeys((code, section) for _, code, section in found))


def _clean_heading(value: Any) -> str:
    heading = re.sub(r"\s+", " ", str(value or "")).strip()
    heading = re.sub(r"^\d+[A-Za-z]*(?:\(\d+\))?\.?\s*", "", heading)
    # OCR sometimes places the opening subsection in the heading.  The actual
    # source text remains in the excerpt; the card title should stay navigable.
    for separator in (".—", "—", ".  "):
        if separator in heading:
            heading = heading.split(separator, 1)[0]
    heading = heading.strip(" .:;—-")
    if not heading or heading.startswith("(") or len(heading) > 140:
        return "Statutory provision"
    return heading


def _clean_excerpt(value: Any, max_chars: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    candidate = text[:max_chars]
    boundary = max(candidate.rfind(". "), candidate.rfind("; "))
    if boundary >= int(max_chars * 0.6):
        candidate = candidate[: boundary + 1]
    else:
        candidate = candidate.rsplit(" ", 1)[0]
    return candidate.rstrip(" ,;:") + " …"


def format_cited_evidence(answer: str, evidence_pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Return clean, deduplicated evidence records cited by the enforced answer."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    for record in evidence_pack.get("retrieved_sections", []):
        key = (_statute_code(record), _section_root(record.get("section")))
        if not key[1]:
            continue
        if key not in by_key:
            order.append(key)
        # Curated records are loaded last and should win if a defensive caller
        # supplies both an OCR stub and its normalized replacement.
        if key not in by_key or record.get("curation"):
            by_key[key] = record

    cited = extract_citation_keys(answer)
    selected_keys = [key for key in cited if key in by_key]
    if not selected_keys:
        selected_keys = order[:3]

    result = []
    for key in selected_keys:
        record = by_key[key]
        code, section = key
        result.append({
            "id": record.get("id"),
            "statute": code,
            "act_number": record.get("act_number", ""),
            "section": section,
            "heading": _clean_heading(record.get("heading")),
            "chapter": record.get("chapter", ""),
            "source": record.get("source", "Official statutory source"),
            "text_snippet": _clean_excerpt(record.get("text")),
            "provenance": record.get("source", "Official statutory source"),
        })
    return result
