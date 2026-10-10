"""Line extraction from PDF pages using word geometry."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pymupdf as fitz

DEVANAGARI_START = "\u0900"
DEVANAGARI_END = "\u097F"
LINE_Y_TOLERANCE = 3.0


@dataclass(frozen=True)
class TextLine:
    page_index: int
    y0: float
    x0: float
    text: str

    @property
    def devanagari_ratio(self) -> float:
        chars = [c for c in self.text if not c.isspace()]
        if not chars:
            return 0.0
        dev = sum(1 for c in chars if DEVANAGARI_START <= c <= DEVANAGARI_END)
        return dev / len(chars)


def group_words_into_lines(page: fitz.Page, page_index: int) -> list[TextLine]:
    words = page.get_text("words")
    buckets: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for w in words:
        x0, y0, _x1, _y1, word, _block, _line, _wno = w
        key = round(y0 / LINE_Y_TOLERANCE) * LINE_Y_TOLERANCE
        buckets[key].append((x0, word))

    lines: list[TextLine] = []
    for y in sorted(buckets):
        parts = sorted(buckets[y], key=lambda p: p[0])
        text = " ".join(p[1] for p in parts).strip()
        if not text:
            continue
        x0 = min(p[0] for p in parts)
        lines.append(TextLine(page_index=page_index, y0=y, x0=x0, text=text))
    return lines


def lines_from_pages(doc: fitz.Document, page_indices: list[int]) -> list[TextLine]:
    out: list[TextLine] = []
    for pi in page_indices:
        out.extend(group_words_into_lines(doc[pi], pi))
    return out


def page_text(doc: fitz.Document, page_indices: list[int]) -> str:
    return "\n".join(doc[pi].get_text() for pi in page_indices)
