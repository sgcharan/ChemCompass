"""Filter OCR garbage and enforce board-style MCQ option quality."""

from __future__ import annotations

import re

from pyq_llm.retrieve import PyqHit

LAZY_OPTION = re.compile(
    r"^(none of these|all of these|both \(a\) and \(b\)|cannot be determined|not defined|option\s+\d)\b",
    re.I,
)

_EN_WORD = re.compile(
    r"\b(the|is|are|of|in|to|and|for|with|from|by|on|at|as|an|a|which|what|why|how|when|due|because)\b",
    re.I,
)


def is_garbled_answer(text: str) -> bool:
    t = text.strip()
    if len(t) < 4:
        return True
    if re.search(r'[!"\#$%]|\.#"', t):
        return True
    letters = sum(1 for c in t if c.isalpha())
    digits = sum(1 for c in t if c.isdigit())
    if letters < 6 and digits >= 3:
        return True
    if re.fullmatch(r"[\d\s.x×\-+*/^()NaNO=]+", t, re.I):
        return True
    if digits >= 8 and letters < 12:
        return True
    if letters > 0 and not _EN_WORD.search(t) and digits > 2:
        return True
    return False


def is_garbled_stem(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 18:
        return True
    if re.search(r'[!"\#$%]|\.#"', t):
        return True
    if t.lower().startswith("(pyq-style)"):
        t = t[11:].strip()
    letter = sum(1 for c in t if c.isalpha())
    if letter < 12:
        return True
    return False


def extract_answer_candidates(answer: str) -> list[str]:
    if not answer:
        return []
    out: list[str] = []
    for chunk in re.split(r"\n+|(?=\([ivx]+\))", answer):
        line = re.sub(r"^\([a-z0-9]+\)\s*", "", chunk.strip(), flags=re.I)
        line = re.sub(r"^\d+\.\s*", "", line)
        if len(line) < 8:
            continue
        if is_garbled_answer(line):
            continue
        out.append(line[:200])
    return out


def is_good_option(text: str) -> bool:
    t = text.strip()
    if len(t) < 10:
        return False
    if LAZY_OPTION.search(t):
        return False
    if is_garbled_answer(t):
        return False
    letters = sum(1 for c in t if c.isalpha())
    if letters < 8:
        return False
    return True


def is_good_pyq_hit(hit: PyqHit) -> bool:
    if is_garbled_stem(hit.text):
        return False
    candidates = extract_answer_candidates(hit.answer or "")
    if candidates:
        return True
    # Stem-only still OK for LLM (infer correct option from NCERT topic)
    return bool(re.search(r"\b(what|which|why|how|define|write|give|name|state|explain)\b", hit.text, re.I))


def filter_quality_hits(hits: list[PyqHit]) -> list[PyqHit]:
    return [h for h in hits if is_good_pyq_hit(h)]
