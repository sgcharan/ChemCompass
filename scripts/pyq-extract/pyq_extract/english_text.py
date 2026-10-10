"""Assemble English question text from PDF clip regions."""

from __future__ import annotations

import re

import pymupdf as fitz

from pyq_extract.filter_en import (
    _garbled_latin_hindi,
    has_english_or_chemistry_signal,
    is_english_content,
)
from pyq_extract.lines import TextLine

ENGLISH_QUESTION_START = re.compile(
    r"^(Give|Which|What|Write|Define|Calculate|Complete|Draw|Arrange|Examine|"
    r"Account|Outline|How|State|Explain|Name|Prepare|Identify|Describe|"
    r"Differentiate|Distinguish|Predict|Justify|List|Why|When|Where|"
    r"After\s+reading|Based\s+on|In\s+reference|All\s+questions)",
    re.I,
)

_INLINE_START = re.compile(
    r"\b(Give|Which|What|Write|Define|Calculate|Complete|Draw|Arrange|Examine|"
    r"Account|Outline|How|State|Explain|Name|Prepare|After\s+reading)\b",
    re.I,
)

_OR_LINE = re.compile(r"^OR\s*\.?\s*$", re.I)
_PAGE_NOISE = re.compile(
    r"(P\.T\.O\.|56tU[t]?\b|\$fltfi|tp\.T\.O\.|^\s*\d{1,2}\s*P\.T\.O\.)",
    re.I,
)


def english_block_start_index(lines: list[TextLine]) -> int:
    """Index of first line where the English question wording begins."""
    candidates: list[int] = []
    for i, line in enumerate(lines):
        t = line.text.strip()
        if _OR_LINE.match(t):
            continue
        if ENGLISH_QUESTION_START.match(t):
            candidates.append(i)
        elif _INLINE_START.search(t) and is_english_content(line):
            candidates.append(i)
    for i, line in enumerate(lines):
        if is_english_content(line) and has_english_or_chemistry_signal(line.text):
            if _garbled_latin_hindi(line.text):
                continue
            if re.search(r"\b(the|of|and|from|with|following|each|one|two)\b", line.text, re.I):
                candidates.append(i)
    if not candidates:
        return 0
    start = min(candidates)
    while start > 0:
        prev = lines[start - 1]
        pt = prev.text.strip()
        if _OR_LINE.match(pt) or _PAGE_NOISE.search(pt):
            break
        if not is_english_content(prev) or not has_english_or_chemistry_signal(pt):
            break
        if _garbled_latin_hindi(pt) and not _CHEM_LINE.search(pt):
            break
        if lines[start].y0 - prev.y0 > 55:
            break
        start -= 1
    return start


_CHEM_LINE = re.compile(
    r"(f\.c\.c|gcm|g/cm|mol-?l|lattice|density|atomic\s+mass|NH2|→|->)",
    re.I,
)
_CHEM_STEM = re.compile(
    r"^(An\s+element|The\s+element|.*\bforms\b.*\b(f\.c\.c|lattice)\b)",
    re.I,
)


def _postfilter_clip_text(text: str) -> str:
    kept: list[str] = []
    for ln in text.splitlines():
        t = ln.strip()
        if not t:
            continue
        if _PAGE_NOISE.search(t):
            continue
        if len(t) <= 3 and not t[0].isdigit():
            continue
        if _garbled_latin_hindi(t) and not ENGLISH_QUESTION_START.match(t):
            continue
        kept.append(t)
    return "\n".join(kept).strip()


def _clean_clip_lines(raw: str, started: bool = False) -> tuple[list[str], bool]:
    lines_out: list[str] = []
    for ln in raw.splitlines():
        t = ln.strip()
        if not t:
            continue
        if not started:
            if ENGLISH_QUESTION_START.match(t):
                started = True
                lines_out.append(t)
                continue
            if _CHEM_STEM.match(t) or (
                _CHEM_LINE.search(t)
                and re.search(r"\b(element|density|lattice|forms|with)\b", t, re.I)
                and not _garbled_latin_hindi(t)
            ):
                started = True
                lines_out.append(t)
                continue
            if _INLINE_START.search(t) and not _garbled_latin_hindi(t):
                started = True
                m = _INLINE_START.search(t)
                if m and m.start() > 0:
                    t = t[m.start() :].strip()
                lines_out.append(t)
            continue
        if _garbled_latin_hindi(t) and not _INLINE_START.search(t):
            continue
        if _PAGE_NOISE.search(t):
            continue
        if len(t) <= 2 and not t[0].isdigit():
            continue
        lines_out.append(t)
    return lines_out, started


def assemble_english_text(
    doc: fitz.Document,
    block_lines: list[TextLine],
    start_index: int,
    ymax_cap: float | None = None,
) -> str:
    if start_index >= len(block_lines):
        return ""

    english_lines = block_lines[start_index:]
    pages = sorted({ln.page_index for ln in english_lines})

    parts: list[str] = []
    started = False
    for pi in pages:
        page = doc[pi]
        page_english = [ln for ln in english_lines if ln.page_index == pi]
        if not page_english:
            continue
        page_ymin = min(ln.y0 for ln in page_english) - 4
        ymax = max(ln.y0 for ln in page_english) + 28
        if ymax_cap is not None:
            ymax = min(ymax, ymax_cap)
        x0 = max(0, min(ln.x0 for ln in page_english) - 8)
        rect = fitz.Rect(x0, max(0, page_ymin - 4), page.rect.width - 36, min(page.rect.height, ymax))
        raw = page.get_text("text", clip=rect)
        clip_lines, started = _clean_clip_lines(raw, started=started)
        if clip_lines:
            parts.append("\n".join(clip_lines))

    if parts:
        merged = "\n".join(parts)
        merged = re.sub(r"\n{3,}", "\n\n", merged).strip()
        return _postfilter_clip_text(merged)

    from pyq_extract.filter_en import filter_block_to_english

    filtered = filter_block_to_english(english_lines)
    return "\n".join(ln.text.strip() for ln in filtered).strip()


def split_or_sections(text: str) -> tuple[str, str | None]:
    lines = text.splitlines()
    main: list[str] = []
    or_parts: list[str] = []
    in_or = False
    for ln in lines:
        if _OR_LINE.match(ln.strip()):
            in_or = True
            continue
        if in_or:
            or_parts.append(ln)
        else:
            main.append(ln)
    or_text = "\n".join(or_parts).strip() if or_parts else None
    return "\n".join(main).strip(), or_text
