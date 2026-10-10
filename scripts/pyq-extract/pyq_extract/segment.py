"""Split PDF into question section and marking scheme section."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pymupdf as fitz

GI_MARKERS = (
    re.compile(r"General\s+Instructions", re.I),
)
MS_MARKERS = (
    re.compile(r"Qn\s+Answers\s+Marks", re.I),
    re.compile(r"CHEMISTRY\s+MARKING\s+SCHEME", re.I),
)
EXAMINER_STOP = re.compile(r"Sr\.\s*No", re.I)


@dataclass(frozen=True)
class DocumentSections:
    question_page_indices: list[int]
    marking_page_indices: list[int]
    general_instructions_page_index: int | None


def _page_matches(page_text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(p.search(page_text) for p in patterns)


def segment_document(doc: fitz.Document) -> DocumentSections:
    gi_page: int | None = None
    ms_start: int | None = None

    for pi in range(len(doc)):
        text = doc[pi].get_text()
        if gi_page is None and _page_matches(text, GI_MARKERS):
            gi_page = pi
        if ms_start is None and _page_matches(text, MS_MARKERS):
            ms_start = pi
            break

    if gi_page is None:
        gi_page = 0

    if ms_start is None:
        ms_start = len(doc)

    question_pages = list(range(gi_page, ms_start))
    marking_pages: list[int] = []
    started = False
    for pi in range(ms_start, len(doc)):
        text = doc[pi].get_text()
        if not started and _page_matches(text, MS_MARKERS):
            started = True
        if not started:
            continue
        if EXAMINER_STOP.search(text) and "Bhatia" in text:
            break
        marking_pages.append(pi)

    if not marking_pages:
        marking_pages = list(range(ms_start, len(doc)))

    return DocumentSections(
        question_page_indices=question_pages,
        marking_page_indices=marking_pages,
        general_instructions_page_index=gi_page,
    )
