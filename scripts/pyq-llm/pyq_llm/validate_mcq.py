from __future__ import annotations

import re
from typing import Any

from pyq_llm.answer_quality import is_good_option

def normalize_opt(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def validate_mcq_payload(data: dict[str, Any], *, source_texts: list[str] | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    text = (data.get("text") or "").strip()
    options = data.get("options") or []
    answer = (data.get("answer") or "").strip()

    if len(text) < 20:
        errors.append("stem too short")
    if len(options) != 4:
        errors.append("need exactly 4 options")
    else:
        norms = [normalize_opt(o) for o in options]
        if len(set(norms)) != 4:
            errors.append("options must be distinct")
        if answer not in options:
            ans_norm = normalize_opt(answer)
            if not any(normalize_opt(o) == ans_norm for o in options):
                errors.append("answer must match one option exactly")
        for opt in options:
            if not is_good_option(str(opt)):
                errors.append("invalid or lazy option text")
                break

    if source_texts:
        stem_norm = normalize_opt(text)
        for src in source_texts:
            if normalize_opt(src) == stem_norm:
                errors.append("duplicate of source PYQ stem")

    return len(errors) == 0, errors
