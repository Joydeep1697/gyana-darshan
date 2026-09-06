"""Deterministic handling of instruction-like text embedded in user documents."""

from __future__ import annotations

import re


_INSTRUCTION_SENTENCE = re.compile(
    r"(?:"
    r"(?:ignore|disregard|override|forget)\b[^.!?]{0,220}\b(?:instruction|system prompt|rule|safeguard)[^.!?]*[.!?]?|"
    r"(?:reveal|exfiltrate|print|show)\b[^.!?]{0,160}\b(?:secret|token|password|system prompt|credential)[^.!?]*[.!?]?|"
    r"\byou are (?:now )?(?:chatgpt|an? (?:unrestricted|jailbroken) assistant)[^.!?]*[.!?]?|"
    r"\b(?:call|use|run|execute)\b[^.!?]{0,120}\b(?:tool|command|terminal|shell)[^.!?]*[.!?]?"
    r")",
    re.IGNORECASE,
)


def sanitize_document_evidence(text: str) -> tuple[str, int]:
    """Remove instruction-like spans while retaining surrounding evidentiary prose.

    The filter is intentionally conservative: it removes only common imperative
    prompt-injection forms and records a neutral marker instead of rewriting the
    source text. The original upload remains unchanged for the document owner.
    """
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        removed += 1
        return " [Instruction-like document text omitted] "

    return _INSTRUCTION_SENTENCE.sub(replace, str(text or "")), removed
