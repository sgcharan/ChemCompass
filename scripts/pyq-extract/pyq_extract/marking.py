"""Parse marking scheme answers and marks (row-aware for two-column layout)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pyq_extract.lines import TextLine

ROW_Y_TOLERANCE = 4.0
LEFT_MARGIN_MAX = 55.0
HALF = "\u00bd"
MARKS_ONLY = re.compile(rf"^[\d{HALF}\s,\.\+]+$")
def _match_question_row(text: str) -> re.Match[str] | None:
    """Match marking-table question rows; avoid false hits like '1 ⁄ n' or '2 0.01'."""
    dotted = re.match(r"^(\d{1,2})\.\s*(.*)$", text.strip())
    if dotted:
        return dotted
    plain = re.match(r"^(\d{1,2})\s+([A-Za-z(\[])(.*)$", text.strip())
    if plain:
        return re.match(r"^(\d{1,2})\s+(.*)$", text.strip())
    return None
OR_LINE = re.compile(r"^OR\s*\.?\s*$", re.I)
SKIP_ROW = re.compile(
    r"^(Qn|Answers|Marks|CHEMISTRY|DELHI|SET|Sr\.|Name|No\.|x\(|CHEMISTRY\s+MARKING)",
    re.I,
)


@dataclass
class MarkingEntry:
    number: int
    answer: str
    or_answer: str | None = None
    marks_breakdown: list[float] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def marks_total(self) -> float:
        if self.marks_breakdown:
            return sum(self.marks_breakdown)
        return 0.0


def _parse_mark_value(token: str) -> float | None:
    token = token.strip().replace(" ", "")
    if not token:
        return None
    total = 0.0
    for part in re.split(r"\+", token):
        part = part.strip().rstrip(",")
        if not part:
            continue
        if part == HALF or part == "1/2":
            total += 0.5
        elif re.match(r"^\d+$", part):
            val = float(part)
            if val > 5:
                return None
            total += val
        elif re.match(r"^\d*\.\d+$", part):
            val = float(part)
            if val > 5:
                return None
            total += val
        else:
            return None
    return total


def _strip_trailing_marks_from_line(text: str) -> tuple[str, list[float]]:
    marks: list[float] = []
    t = text
    while True:
        m = re.search(rf"\s+([\d{HALF}]+(?:\s*,\s*[\d{HALF}]+)*)\s*$", t)
        if not m:
            break
        chunk = m.group(1)
        parsed = [_parse_mark_value(p) for p in re.split(r",", chunk)]
        if any(p is None for p in parsed):
            break
        marks.extend([p for p in parsed if p is not None])
        t = t[: m.start()].rstrip()
    return t, marks


def _group_rows(lines: list[TextLine]) -> list[str]:
    sorted_lines = sorted(lines, key=lambda ln: (ln.page_index, ln.y0, ln.x0))
    rows: list[list[TextLine]] = []
    current: list[TextLine] = []
    current_y: float | None = None

    for line in sorted_lines:
        if current_y is None or abs(line.y0 - current_y) > ROW_Y_TOLERANCE:
            if current:
                rows.append(current)
            current = [line]
            current_y = line.y0
        else:
            current.append(line)
    if current:
        rows.append(current)

    merged: list[str] = []
    for row in rows:
        text = " ".join(ln.text.strip() for ln in sorted(row, key=lambda l: l.x0)).strip()
        if text:
            merged.append(text)
    return merged


def parse_marking_scheme(lines: list[TextLine]) -> dict[int, MarkingEntry]:
    entries: dict[int, MarkingEntry] = {}
    current: MarkingEntry | None = None
    in_or = False
    or_parts: list[str] = []
    started = False

    def close_current() -> None:
        nonlocal current, in_or, or_parts
        if current is None:
            return
        if or_parts:
            current.or_answer = "\n".join(or_parts).strip()
        entries[current.number] = current
        current = None
        in_or = False
        or_parts = []

    def append_answer(text: str, marks: list[float]) -> None:
        if current is None or not text:
            return
        if current.answer:
            current.answer += "\n" + text
        else:
            current.answer = text
        current.marks_breakdown.extend(marks)

    for row_text in _group_rows(lines):
        t = row_text.strip()
        if not t:
            continue
        if re.search(r"Qn\s+Answers\s+Marks", t, re.I):
            started = True
            continue
        if not started:
            continue
        if SKIP_ROW.search(t) and not re.match(r"^\d", t):
            continue

        if OR_LINE.match(t):
            in_or = True
            continue

        m = _match_question_row(t)
        if m:
            num = int(m.group(1))
            if num > 30:
                continue
            rest, inline_marks = _strip_trailing_marks_from_line(m.group(2))
            close_current()
            current = MarkingEntry(number=num, answer=rest.strip())
            current.marks_breakdown.extend(inline_marks)
            in_or = False
            continue

        if current is None:
            continue

        if MARKS_ONLY.match(t):
            for token in re.split(r"[,+]", t):
                val = _parse_mark_value(token)
                if val is not None:
                    current.marks_breakdown.append(val)
            continue

        stripped, inline_marks = _strip_trailing_marks_from_line(t)
        if in_or:
            if stripped:
                or_parts.append(stripped)
            if inline_marks:
                current.marks_breakdown.extend(inline_marks)
        else:
            append_answer(stripped, inline_marks)

    close_current()

    for e in entries.values():
        e.answer = e.answer.strip()
    return entries
