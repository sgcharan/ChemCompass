"""Derive paper metadata from file path."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PaperSource:
    year: int | None
    exam: str | None
    region: str | None
    set: int | None


_FILENAME_RE = re.compile(
    r"chemistry-(\d{4})-([\w-]+)-exams-([\w-]+)-set-(\d+)",
    re.I,
)


def parse_metadata(pdf_path: Path) -> PaperSource:
    stem = pdf_path.stem.lower()
    m = _FILENAME_RE.search(stem)
    if not m:
        return PaperSource(year=None, exam=None, region=None, set=None)
    year = int(m.group(1))
    exam = m.group(2).replace("-", " ")
    region = m.group(3)
    set_num = int(m.group(4))
    return PaperSource(year=year, exam=exam, region=region, set=set_num)


def paper_id(pdf_path: Path, source: PaperSource) -> str:
    if source.year and source.region and source.set is not None:
        region = source.region.replace(" ", "-")
        exam = (source.exam or "exam").replace(" ", "-")
        return f"pyq-{source.year}-{exam}-{region}-set-{source.set}"
    return f"pyq-{pdf_path.stem}"
