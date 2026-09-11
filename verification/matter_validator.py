"""Validation and risk annotation for deterministic matter extraction."""
from __future__ import annotations

from datetime import date
from typing import Any


def validate_matter_data(data: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    errors: list[str] = []
    if not any((data.get("parties") or {}).values()):
        errors.append("parties_empty")
    dates = [data.get("next_hearing_date")] + [item.get("due_date") for item in data.get("obligations", [])]
    for value in filter(None, dates):
        try:
            if date.fromisoformat(value) < today:
                errors.append(f"past_date:{value}")
        except ValueError:
            errors.append(f"invalid_date:{value}")
    return {"valid": not errors, "errors": errors}
