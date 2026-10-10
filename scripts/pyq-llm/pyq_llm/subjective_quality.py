"""Reject merged / mis-tagged PYQ rows for printable subjective sections."""

from __future__ import annotations

import re

# Multiple board questions often concatenated in one OCR row (wrong rubric marks).
_DISTINCT_STARTERS = re.compile(
    r"(?:^|\n)\s*(?:"
    r"How many\b|"
    r"Define\b|"
    r"Assuming\b|"
    r"Calculate\b|"
    r"What is\b|"
    r"Write the formula\b|"
    r"Draw the structure\b|"
    r"Describe a chemical test\b"
    r")",
    re.I,
)

_MAX_LEN = {1: 400, 2: 520, 3: 800, 4: 1000, 5: 1400}


def distinct_question_starts(text: str) -> int:
    return len(_DISTINCT_STARTERS.findall(text or ""))


def is_merged_subjective_blob(text: str) -> bool:
    return distinct_question_starts(text) >= 3


def is_good_subjective_text(text: str, *, marks: int | None = None) -> bool:
    t = (text or "").strip()
    if len(t) < 12:
        return False
    if is_merged_subjective_blob(t):
        return False
    if marks is not None:
        cap = _MAX_LEN.get(int(marks), 2000)
        if len(t) > cap:
            return False
    return True
