"""Human-readable labels for PYQ corpus IDs."""

from __future__ import annotations

import re

from pyq_llm.retrieve import PyqHit


def pyq_id_to_label(pyq_id: str) -> str:
    """e.g. pyq-2014-main-delhi-set-1:6 → CBSE 2014 Main, Delhi Set 1, Q6"""
    if ":" not in pyq_id:
        return pyq_id
    paper, qnum = pyq_id.rsplit(":", 1)
    m = re.match(r"pyq-(\d{4})-(\w+)-(\w+)-set-(\d+)", paper)
    if m:
        year, exam, region, set_n = m.groups()
        exam_t = exam.replace("-", " ").title()
        region_t = region.replace("-", " ").title()
        return f"CBSE {year} {exam_t}, {region_t} Set {set_n}, Q{qnum}"
    return f"{paper}, Q{qnum}"


def primary_stem(hit: PyqHit) -> str:
    """First English question line from PYQ text (MCQ stem)."""
    for line in hit.text.splitlines():
        t = line.strip()
        if len(t) < 10:
            continue
        if t.endswith("?") or re.match(r"^(What|Which|Why|How|Define|Give|Write|Name|State|Explain|Calculate)", t, re.I):
            return t
    first = hit.text.strip().splitlines()[0].strip()
    return first if first else hit.text.strip()[:300]


def marking_snippet(hit: PyqHit, max_len: int = 200) -> str:
    ans = (hit.answer or "").strip()
    if not ans:
        return ""
    line = ans.splitlines()[0].strip()
    return line[:max_len] + ("…" if len(line) > max_len else "")


def attribution_dict(hit: PyqHit) -> dict[str, str]:
    return {
        "basedOnPyqId": hit.id,
        "basedOnLabel": pyq_id_to_label(hit.id),
        "basedOnStem": primary_stem(hit),
        "basedOnMarkingAnswer": marking_snippet(hit),
    }
