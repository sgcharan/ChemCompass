from __future__ import annotations

import json
import re
from typing import Any, Literal

import httpx

from pyq_llm.answer_quality import extract_answer_candidates, is_good_option
from pyq_llm.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_CONFIGURED,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    active_llm_provider,
    openai_auth_key,
)
from pyq_llm.chem_format import format_mcq_fields
from pyq_llm.pyq_ref import attribution_dict, primary_stem
from pyq_llm.retrieve import PyqHit
from pyq_llm.validate_mcq import validate_mcq_payload

StemMode = Literal["strict", "creative", "mix"]
ResolvedStemMode = Literal["strict", "creative"]

SYSTEM_STRICT = """You convert CBSE Class 12 Chemistry PYQs into four-option MCQs using NCERT Chemistry (Part I & II).

The board question stem is FIXED (provided separately). Do NOT rewrite the stem in your JSON.

Your only task: write four answer choices (options) so the student must think deeper than a one-line definition.
- One option must match the marking-scheme / NCERT concept (paraphrase allowed; be chemically correct).
- Three options must be plausible wrong answers: common misconceptions, swapped terms, or closely related NCERT facts from the same chapter.
- NEVER use: "None of these", "All of these", "Cannot be determined", or bare calculation fragments as options.
- Use plain text for formulas (e.g. H2O, C6H12O6) — do NOT use HTML tags like <sub> or <sup>.

Respond with JSON only:
{"options":[exactly 4 strings],"answer":"must equal one option exactly","explanation":"1-2 lines","sourcePyqIds":["primary-id"]}
"""

SYSTEM_CREATIVE = """You write NEW CBSE Class 12 Chemistry MCQs (1 mark) aligned with NCERT Chemistry (Part I & II).

Use the provided PYQ snippets only as topic and difficulty grounding — do NOT copy the PYQ stem verbatim.
Write a fresh question on the same concept that would still feel like a board paper item.

Rules:
- All four options must be complete plausible statements grounded in NCERT for that chapter.
- Wrong options: common misconceptions or closely related facts (not joke answers).
- NEVER use: "None of these", "All of these", "Cannot be determined", or bare formulas as options.
- Plain text formulas only (H2O, NaCl) — no HTML <sub> or <sup>.

Respond with JSON only:
{"text":"new question stem","options":[exactly 4 strings],"answer":"must equal one option exactly","explanation":"1-2 lines","sourcePyqIds":["id-of-primary-pyq-used"]}
"""


def resolve_stem_mode(stem_mode: StemMode, item_index: int) -> ResolvedStemMode:
    if stem_mode == "mix":
        return "creative" if item_index % 2 else "strict"
    return stem_mode


def _format_context(hits: list[PyqHit]) -> str:
    blocks = []
    for h in hits:
        cands = extract_answer_candidates(h.answer or "")
        ans_note = "\n".join(f"  - {c}" for c in cands[:3]) if cands else "  (use NCERT for correct concept)"
        blocks.append(
            f"ID: {h.id}\nChapter hint: {h.chapter}\nMarks: {h.marks}\nQ: {h.text}\n"
            f"Marking scheme (may be OCR-noisy):\n{h.answer[:400]}\n"
            f"Usable answer lines:\n{ans_note}\n---"
        )
    return "\n".join(blocks)


def _parse_json_content(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


async def _call_openai(system: str, user: str, temperature: float) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if "api.openai.com" in OPENAI_BASE_URL:
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {openai_auth_key()}"},
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_json_content(content)


async def _call_ollama(system: str, user: str, temperature: float) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": temperature},
            },
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return _parse_json_content(content)


async def _call_gemini(system: str, user: str, temperature: float) -> dict[str, Any]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    prompt = f"{system}\n\n{user}"
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            url,
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            },
        )
        resp.raise_for_status()
        body = resp.json()
        parts = body["candidates"][0]["content"]["parts"]
        content = parts[0].get("text", "")
        return _parse_json_content(content)


async def _call_llm(system: str, user: str, temperature: float = 0.65) -> dict[str, Any]:
    provider = active_llm_provider()
    if provider == "gemini":
        return await _call_gemini(system, user, temperature)
    if provider == "ollama":
        return await _call_ollama(system, user, temperature)
    if provider == "openai":
        return await _call_openai(system, user, temperature)
    raise ValueError("No LLM provider configured")


def _build_user_prompt(
    hits: list[PyqHit],
    *,
    chapter: str | None,
    difficulty: str,
    resolved: ResolvedStemMode,
) -> tuple[str, str]:
    primary = hits[0]
    ch = chapter or primary.chapter or "Class 12 Chemistry"

    if resolved == "strict":
        fixed_stem = primary_stem(primary)
        user = (
            f"NCERT chapter: {ch}\nDifficulty: {difficulty}\n\n"
            f"FIXED QUESTION STEM (do not change): {fixed_stem}\n\n"
            f"Primary PYQ id: {primary.id}\n"
            f"Marking scheme answer:\n{primary.answer[:500]}\n\n"
            f"Additional context PYQs:\n{_format_context(hits[1:])}\n\n"
            "Write only the four options JSON for this stem."
        )
        return SYSTEM_STRICT, user

    user = (
        f"NCERT chapter: {ch}\nDifficulty: {difficulty}\n\n"
        f"Primary PYQ to ground on (id {primary.id}):\n"
        f"Q: {primary.text}\nA: {primary.answer[:500]}\n\n"
        f"More PYQs for context:\n{_format_context(hits)}\n\n"
        "Generate one NEW four-option MCQ on the same concept (new stem)."
    )
    return SYSTEM_CREATIVE, user


async def generate_mcq(
    hits: list[PyqHit],
    *,
    chapter: str | None = None,
    difficulty: str = "board",
    stem_mode: StemMode = "strict",
    item_index: int = 0,
) -> dict[str, Any]:
    if not hits:
        raise ValueError("no PYQ context for generation")

    if not LLM_CONFIGURED:
        raise ValueError(
            "LLM not configured. Use local Ollama (USE_OLLAMA=1), LM Studio (OPENAI_BASE_URL), "
            "GEMINI_API_KEY, or OPENAI_API_KEY — see scripts/pyq-llm/README.md"
        )

    primary = hits[0]
    resolved = resolve_stem_mode(stem_mode, item_index)
    source_texts = [h.text for h in hits] if resolved == "creative" else None
    system, user = _build_user_prompt(
        hits, chapter=chapter, difficulty=difficulty, resolved=resolved
    )

    last_errors: list[str] = []
    for attempt in range(3):
        temp = 0.55 + attempt * 0.15
        if resolved == "creative":
            temp = min(0.85, temp + 0.1)
        data = await _call_llm(system, user, temperature=temp)
        if not data.get("sourcePyqIds"):
            data["sourcePyqIds"] = [primary.id]
        data["chapter"] = chapter or primary.chapter
        data["mode"] = active_llm_provider() or "llm"
        data["stemMode"] = resolved
        data.update(attribution_dict(primary))

        if resolved == "strict":
            data["text"] = primary_stem(primary)
        elif not (data.get("text") or "").strip():
            last_errors = ["creative mode missing question text"]
            continue

        options = data.get("options") or []
        if not all(is_good_option(str(o)) for o in options):
            last_errors = ["one or more options failed quality check (lazy or garbled)"]
            continue

        ok, errors = validate_mcq_payload(data, source_texts=source_texts)
        if ok:
            return format_mcq_fields(data)
        last_errors = errors

    raise ValueError(f"MCQ generation failed validation after retries: {last_errors}")
