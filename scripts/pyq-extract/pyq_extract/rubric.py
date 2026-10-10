"""Parse mark rubric from General Instructions."""

from __future__ import annotations

import re
from dataclasses import dataclass

_RUBRIC_LINE = re.compile(
    r"Question\s+numbers?\s+(\d+)\s+to\s+(\d+).*?"
    r"carry\s+(\d+|I|i)\s+mark",
    re.I | re.DOTALL,
)


def _normalize_instructions(text: str) -> str:
    out = text
    out = re.sub(
        r"Question\s+numbers?\s+I\s+to\s+I",
        "Question numbers 1 to 8",
        out,
        flags=re.I,
    )
    out = re.sub(r"carry\s+i\s+marks", "carry 3 marks", out, flags=re.I)
    out = re.sub(r"carry\s+I\s+mark", "carry 1 mark", out, flags=re.I)
    out = re.sub(r"5\s+mnrks", "5 marks", out, flags=re.I)
    return out


def _parse_mark_token(tok: str) -> int:
    tok = tok.strip().lower()
    if tok in ("i", "l"):
        return 1
    return int(tok)


@dataclass(frozen=True)
class Rubric:
    ranges: tuple[tuple[int, int, int], ...]

    def marks_for(self, question_number: int) -> int | None:
        for start, end, marks in self.ranges:
            if start <= question_number <= end:
                return marks
        return None

    def to_dict(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for start, end, marks in self.ranges:
            out[f"{start}-{end}"] = marks
        return out


def parse_rubric(instructions_text: str) -> Rubric:
    text = _normalize_instructions(instructions_text)
    ranges: list[tuple[int, int, int]] = []
    for m in _RUBRIC_LINE.finditer(text):
        start, end, mark_tok = int(m.group(1)), int(m.group(2)), m.group(3)
        ranges.append((start, end, _parse_mark_token(mark_tok)))
    if not ranges:
        ranges = [(1, 8, 1), (9, 18, 2), (19, 27, 3), (28, 30, 5)]
    return Rubric(ranges=tuple(ranges))
