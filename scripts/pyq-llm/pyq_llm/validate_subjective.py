"""Validate LLM subjective question payloads."""

from __future__ import annotations

_MAX_LEN = {2: 1200, 3: 1600, 4: 2000, 5: 2400}


def validate_subjective_payload(
    data: dict,
    *,
    slot_marks: int,
    strict_stem: str | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    text = (data.get("text") or "").strip()
    answer = (data.get("answer") or "").strip()
    if len(text) < 12:
        errors.append("question text too short")
    if len(answer) < 4:
        errors.append("answer too short")
    cap = _MAX_LEN.get(slot_marks, 2500)
    if len(text) > cap:
        errors.append("question text too long")
    if strict_stem and text.strip() != strict_stem.strip():
        errors.append("strict mode stem mismatch")
    return (len(errors) == 0, errors)
