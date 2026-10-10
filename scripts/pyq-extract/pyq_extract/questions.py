"""Parse English question blocks Q1–30."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf as fitz

from pyq_extract.english_text import (
    assemble_english_text,
    english_block_start_index,
    split_or_sections,
)
from pyq_extract.filter_en import filter_block_to_english
from pyq_extract.lines import TextLine

LEFT_MARGIN_MAX = 62.0
OR_LINE = re.compile(r"^OR\s*\.?\s*$", re.I)
NUMERIC_START = re.compile(r"^(\d{1,2})\.\s*(.*)$")

OCR_ALIASES: dict[int, re.Pattern[str]] = {
    11: re.compile(r"^n\.\s*(.*)$", re.I),
    12: re.compile(r"^t2\.\s*(.*)$", re.I),
    13: re.compile(r"^(?:I\s*3\.|3\.)\s*(.*)$", re.I),
    17: re.compile(r"^L7\s*\.?\s*(.*)$", re.I),
    21: re.compile(r"^2t\.\s*(.*)$", re.I),
    29: re.compile(r"^2s\.\s*(.*)$", re.I),
}


@dataclass
class ParsedQuestion:
    number: int
    text: str
    or_text: str | None = None
    line_refs: list[TextLine] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def _try_question_start(line: TextLine, expected: int) -> tuple[int, str] | None:
    t = line.text.strip()
    if is_noise_start(t):
        return None

    margin_ok = line.x0 <= LEFT_MARGIN_MAX
    wide_ok = line.x0 <= 90.0

    m = NUMERIC_START.match(t)
    if m:
        num = int(m.group(1))
        if num == expected and (margin_ok or (num >= 28 and wide_ok)):
            return num, (m.group(2) or "").strip()

    if not margin_ok:
        return None

    alias = OCR_ALIASES.get(expected)
    if alias:
        am = alias.match(t)
        if am:
            rest = (am.group(1) or "").strip()
            return expected, rest
    return None


def is_noise_start(t: str) -> bool:
    return bool(re.search(r"P\.T\.O\.", t, re.I))


def find_question_body_start(lines: list[TextLine]) -> int:
    for i, line in enumerate(lines):
        if re.search(r"calculators\s+is\s+not\s+allowed", line.text, re.I):
            return i + 1
        if NUMERIC_START.match(line.text.strip()) and line.x0 < LEFT_MARGIN_MAX:
            if line.text.strip().startswith("1."):
                return i
    return 0


def split_raw_question_blocks(lines: list[TextLine]) -> list[tuple[int, list[TextLine]]]:
    start_idx = find_question_body_start(lines)
    body = lines[start_idx:]
    boundaries: list[tuple[int, int, str]] = []
    expected = 1

    for i, line in enumerate(body):
        hit = _try_question_start(line, expected)
        if hit is None:
            continue
        num, _rest = hit
        boundaries.append((i, num, line.text))
        expected += 1
        if expected > 30:
            break

    blocks: list[tuple[int, list[TextLine]]] = []
    for bi, (i, num, _t) in enumerate(boundaries):
        end = boundaries[bi + 1][0] if bi + 1 < len(boundaries) else len(body)
        block_lines = body[i:end]
        blocks.append((num, block_lines))
    return blocks


def _clip_ymax_cap(
    block_lines: list[TextLine],
    next_block_lines: list[TextLine] | None,
) -> float | None:
    if not block_lines or not next_block_lines:
        return None
    last = block_lines[-1]
    nxt = next_block_lines[0]
    if nxt.page_index != last.page_index:
        return None
    if nxt.y0 <= last.y0:
        return None
    return nxt.y0 - 2.0


def parse_questions(all_lines: list[TextLine], doc: fitz.Document) -> list[ParsedQuestion]:
    blocks = split_raw_question_blocks(all_lines)
    questions: list[ParsedQuestion] = []

    for bi, (num, block_lines) in enumerate(blocks):
        next_bl = blocks[bi + 1][1] if bi + 1 < len(blocks) else None
        ymax_cap = _clip_ymax_cap(block_lines, next_bl)
        start_idx = english_block_start_index(block_lines)
        text_raw = assemble_english_text(doc, block_lines, start_idx, ymax_cap=ymax_cap)
        text, or_text = split_or_sections(text_raw)

        english_lines = filter_block_to_english(block_lines[start_idx:])
        if not english_lines:
            english_lines = block_lines[start_idx:]

        questions.append(
            ParsedQuestion(
                number=num,
                text=text,
                or_text=or_text,
                line_refs=english_lines,
            )
        )

    return questions
