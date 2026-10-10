"""Plan corpus vs LLM per paper slot from AI blend level."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from pyq_llm.mark_spread import SectionCounts

SlotMode = Literal["corpus", "llm"]


@dataclass(frozen=True)
class PaperSlot:
    section_key: str
    title: str
    instruction: str
    mark_value: int
    kind: str
    section_label: str
    index_in_section: int
    mode: SlotMode


def build_slot_list(counts: SectionCounts) -> list[PaperSlot]:
    slots: list[PaperSlot] = []

    def add(
        key: str,
        title: str,
        instruction: str,
        mark: int,
        kind: str,
        label: str,
        n: int,
    ) -> None:
        for i in range(n):
            slots.append(
                PaperSlot(
                    section_key=key,
                    title=title,
                    instruction=instruction,
                    mark_value=mark,
                    kind=kind,
                    section_label=label,
                    index_in_section=i,
                    mode="corpus",
                )
            )

    add(
        "A",
        "SECTION A",
        "Multiple-choice questions from previous-year topics (1 mark each).",
        1,
        "mcq",
        "Section A",
        counts.one,
    )
    add(
        "B",
        "SECTION B",
        "Very short answer questions from previous year papers (2 marks each).",
        2,
        "vsa",
        "Section B",
        counts.vsa,
    )
    add(
        "C",
        "SECTION C",
        "Short answer questions from previous year papers (3 marks each).",
        3,
        "sa",
        "Section C",
        counts.sa,
    )
    if counts.case > 0:
        add(
            "D",
            "SECTION D",
            "Previous year questions (4 marks each).",
            4,
            "case",
            "Section D",
            counts.case,
        )
    add(
        "E",
        "SECTION E",
        "Long answer questions from previous year papers (5 marks each).",
        5,
        "la",
        "Section E",
        counts.la,
    )
    return slots


def _evenly_spaced_indices(n: int, pick: int) -> set[int]:
    if pick <= 0:
        return set()
    if pick >= n:
        return set(range(n))
    if pick == 1:
        return {n // 2}
    out: set[int] = set()
    for i in range(pick):
        idx = int(round(i * (n - 1) / (pick - 1)))
        out.add(min(n - 1, max(0, idx)))
    return out


def plan_slot_modes(slots: list[PaperSlot], ai_level: int) -> list[PaperSlot]:
    """Return slots with mode corpus or llm from ai_level 0–100."""
    n = len(slots)
    if n == 0:
        return []
    level = max(0, min(100, int(ai_level)))
    if level >= 100:
        return [replace(s, mode="llm") for s in slots]
    if level <= 0:
        return [replace(s, mode="corpus") for s in slots]

    n_ai = round(level / 100 * n)
    ai_idx = _evenly_spaced_indices(n, n_ai)
    planned: list[PaperSlot] = []
    for i, s in enumerate(slots):
        mode: SlotMode = "llm" if i in ai_idx else "corpus"
        planned.append(replace(s, mode=mode))
    return planned
