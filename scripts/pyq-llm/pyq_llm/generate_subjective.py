"""LLM subjective (2–5 mark) questions from PYQ context."""

from __future__ import annotations

from typing import Any

from pyq_llm.chem_format import format_chemistry_display
from pyq_llm.config import LLM_CONFIGURED, active_llm_provider
from pyq_llm.generate_mcq import (
    ResolvedStemMode,
    StemMode,
    _call_llm,
    _format_context,
    resolve_stem_mode,
)
from pyq_llm.pyq_ref import attribution_dict, primary_stem
from pyq_llm.retrieve import PyqHit
from pyq_llm.validate_subjective import validate_subjective_payload

SYSTEM_STRICT_SUBJ = """You write marking-scheme answers for CBSE Class 12 Chemistry short/long questions.

The question stem is FIXED (provided). Do NOT rewrite the stem in your JSON.

Respond with JSON only:
{"answer":"model answer suitable for the given marks","explanation":"optional 1 line","sourcePyqIds":["primary-id"]}
"""

SYSTEM_CREATIVE_SUBJ = """You write NEW CBSE Class 12 Chemistry board-style subjective questions aligned with NCERT.

Use PYQ snippets as topic/difficulty grounding — do not copy stems verbatim unless natural.

Respond with JSON only:
{"text":"question stem appropriate for the mark weight","answer":"concise model answer","explanation":"optional","sourcePyqIds":["primary-id"]}
"""


def _build_subjective_prompt(
    hits: list[PyqHit],
    *,
    chapter: str | None,
    slot_marks: int,
    resolved: ResolvedStemMode,
) -> tuple[str, str]:
    primary = hits[0]
    ch = chapter or primary.chapter or "Class 12 Chemistry"
    if resolved == "strict":
        fixed = primary_stem(primary)
        user = (
            f"NCERT chapter: {ch}\nMarks: {slot_marks}\n\n"
            f"FIXED STEM:\n{fixed}\n\n"
            f"Primary PYQ id: {primary.id}\n"
            f"Marking scheme:\n{primary.answer[:600]}\n\n"
            f"Context:\n{_format_context(hits[1:])}\n\n"
            "Write the model answer JSON only."
        )
        return SYSTEM_STRICT_SUBJ, user

    user = (
        f"NCERT chapter: {ch}\nMarks: {slot_marks}\n\n"
        f"Primary PYQ (id {primary.id}):\nQ: {primary.text}\nA: {primary.answer[:500]}\n\n"
        f"More context:\n{_format_context(hits)}\n\n"
        f"Write one NEW {slot_marks}-mark board question and answer."
    )
    return SYSTEM_CREATIVE_SUBJ, user


async def generate_subjective(
    hits: list[PyqHit],
    *,
    slot_marks: int,
    chapter: str | None = None,
    stem_mode: StemMode = "mix",
    item_index: int = 0,
) -> dict[str, Any]:
    if not hits:
        raise ValueError("no PYQ context for subjective generation")
    if not LLM_CONFIGURED:
        raise ValueError("LLM not configured")

    primary = hits[0]
    resolved = resolve_stem_mode(stem_mode, item_index)
    strict_stem = primary_stem(primary) if resolved == "strict" else None
    system, user = _build_subjective_prompt(
        hits, chapter=chapter, slot_marks=slot_marks, resolved=resolved
    )

    last_errors: list[str] = []
    for attempt in range(3):
        temp = 0.55 + attempt * 0.12
        data = await _call_llm(system, user, temperature=temp)
        if not data.get("sourcePyqIds"):
            data["sourcePyqIds"] = [primary.id]
        data["chapter"] = chapter or primary.chapter
        data["mode"] = active_llm_provider() or "llm"
        data["stemMode"] = resolved
        data.update(attribution_dict(primary))
        if resolved == "strict":
            data["text"] = strict_stem or primary_stem(primary)
        elif not (data.get("text") or "").strip():
            last_errors = ["creative subjective missing text"]
            continue

        ok, errors = validate_subjective_payload(
            data, slot_marks=slot_marks, strict_stem=strict_stem
        )
        if ok:
            data["text"] = format_chemistry_display(str(data["text"]))
            data["answer"] = format_chemistry_display(str(data["answer"]))
            return data
        last_errors = errors

    raise ValueError(f"Subjective generation failed: {last_errors}")
