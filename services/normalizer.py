"""Normalizer -- normalize IDs, text, credits, and source metadata."""

from __future__ import annotations

import re

_COURSE_ID_PATTERN = re.compile(r"^([A-Za-z]{2,4})[\s-]*(\d{3})$")


def normalize_course_id(raw: str) -> str:
    """Normalize a course ID like 'CIS110', 'CIS 110', or 'COM-231' to one canonical form (e.g. 'CIS110')."""
    text = raw.strip().upper()
    match = _COURSE_ID_PATTERN.match(text)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    return re.sub(r"[\s-]+", "", text)


def normalize_text(raw: str | None) -> str:
    """Collapse internal whitespace and strip a text field; returns '' for missing values."""
    if not isinstance(raw, str):
        return ""
    return re.sub(r"\s+", " ", raw).strip()


def normalize_credits(raw: object) -> int:
    """Coerce a skill-level credit cell to an int, treating blank, zero, or non-numeric values as 0 (no credit)."""
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    return 0
