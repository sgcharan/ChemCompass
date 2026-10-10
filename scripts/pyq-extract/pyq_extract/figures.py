"""Crop diagram regions for questions with little text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz

from pyq_extract.lines import TextLine
from pyq_extract.questions import ParsedQuestion

MIN_TEXT_LEN_FOR_SKIP = 120
CLIP_PADDING = 8.0
RENDER_MATRIX = fitz.Matrix(2.0, 2.0)


@dataclass(frozen=True)
class FigureAsset:
    path: str
    page_index: int
    note: str | None = None


def _question_y_bounds(q: ParsedQuestion) -> dict[int, tuple[float, float]]:
    by_page: dict[int, list[float]] = {}
    for ref in q.line_refs:
        by_page.setdefault(ref.page_index, []).append(ref.y0)
    return {pi: (min(ys), max(ys) + 40) for pi, ys in by_page.items()}


def crop_question_figures(
    doc: fitz.Document,
    question: ParsedQuestion,
    assets_dir: Path,
    paper_id: str,
) -> list[FigureAsset]:
    if len(question.text) >= MIN_TEXT_LEN_FOR_SKIP:
        return []

    assets_dir.mkdir(parents=True, exist_ok=True)
    bounds = _question_y_bounds(question)
    figures: list[FigureAsset] = []
    fig_idx = 0

    for page_index, (y0, y1) in bounds.items():
        page = doc[page_index]
        if not page.get_images(full=True):
            continue
        rect = fitz.Rect(0, max(0, y0 - CLIP_PADDING), page.rect.width, min(page.rect.height, y1 + CLIP_PADDING))
        if rect.height < 20:
            continue
        fig_idx += 1
        filename = f"{paper_id}_q{question.number}_fig{fig_idx}.png"
        out_path = assets_dir / filename
        pix = page.get_pixmap(matrix=RENDER_MATRIX, clip=rect, alpha=False)
        pix.save(str(out_path))
        figures.append(
            FigureAsset(
                path=str(out_path),
                page_index=page_index,
                note="cropped region (low text layer)",
            )
        )
    return figures
