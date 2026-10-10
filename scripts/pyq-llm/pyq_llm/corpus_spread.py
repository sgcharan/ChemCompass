"""Adjust CBSE section counts to what the local PYQ corpus can supply."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from pyq_llm.mark_spread import SectionCounts, cbse_spread_for_total, marks_from_counts

# Mirrors src/generator.ts PAPER_MARKS_OPTIONS (5–70 step 5)
PAPER_MARKS_CANDIDATES: tuple[int, ...] = tuple(range(5, 71, 5))


def _subjective_count(
    db_path: Path,
    marks: int,
    chapters: list[str] | None,
    *,
    usable_only: bool,
) -> int:
    if not db_path.is_file():
        return 0
    conn = sqlite3.connect(db_path)
    sql = """
        SELECT COUNT(*) FROM questions
        WHERE marks = ?
          AND length(trim(text)) >= 15
          AND length(trim(coalesce(answer, ''))) >= 1
    """
    params: list[object] = [marks]
    if usable_only:
        sql += " AND usable = 1"
    if chapters:
        placeholders = ",".join("?" * len(chapters))
        sql += f" AND chapter IN ({placeholders})"
        params.extend(chapters)
    n = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return int(n)


def _mcq_seed_count(db_path: Path, chapters: list[str] | None) -> int:
    """Rows usable as LLM MCQ seeds (1-mark preferred, any short usable PYQ)."""
    if not db_path.is_file():
        return 0
    conn = sqlite3.connect(db_path)
    sql = """
        SELECT COUNT(*) FROM questions
        WHERE marks IN (1, 2)
          AND length(trim(text)) >= 18
          AND length(trim(coalesce(answer, ''))) >= 1
    """
    params: list[object] = []
    if chapters:
        placeholders = ",".join("?" * len(chapters))
        sql += f" AND chapter IN ({placeholders})"
        params.extend(chapters)
    n = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return int(n)


def rebalance_counts_for_corpus(
    db_path: Path,
    counts: SectionCounts,
    chapters: list[str] | None,
) -> tuple[SectionCounts, list[str]]:
    """
    CBSE papers include 4-mark case studies; many extractions have no marks=4 rows.
    Swap missing bands for nearby weights while keeping the same total marks.
    """
    notes: list[str] = []
    c = counts

    avail4 = _subjective_count(db_path, 4, chapters, usable_only=False)
    if c.case > 0 and avail4 < c.case:
        short = c.case - avail4
        c = SectionCounts(
            one=c.one,
            vsa=c.vsa + 2 * short,
            sa=c.sa,
            case=max(0, c.case - short),
            la=c.la,
        )
        notes.append(
            "Your corpus has no 4-mark PYQ rows; those slots are filled with extra 2-mark questions."
        )

    target = marks_from_counts(counts)
    m = marks_from_counts(c)
    guard = 0
    while m != target and guard < 50:
        guard += 1
        if m < target:
            c = SectionCounts(one=c.one, vsa=c.vsa + 1, sa=c.sa, case=c.case, la=c.la)
            m += 2
        elif m > target:
            if c.vsa > 0:
                c = SectionCounts(one=c.one, vsa=c.vsa - 1, sa=c.sa, case=c.case, la=c.la)
                m -= 2
            elif c.sa > 0:
                c = SectionCounts(one=c.one, vsa=c.vsa, sa=c.sa - 1, case=c.case, la=c.la)
                m -= 3
            else:
                break

    seeds = _mcq_seed_count(db_path, chapters)
    if c.one > 0 and seeds == 0:
        notes.append(
            "No PYQ rows found to seed Section A MCQs — check corpus build or chapter filters."
        )
    elif c.one > seeds:
        notes.append(
            f"Section A plans {c.one} MCQs but only ~{seeds} distinct PYQ seeds exist; "
            "some MCQs may reuse topics or fail if the LLM errors."
        )

    return c, notes


def subjective_supply(
    db_path: Path,
    chapters: list[str] | None,
    *,
    usable_only: bool = False,
) -> dict[int, int]:
    """Question counts per board mark band (estimate for capacity; not quality-filtered)."""
    bands = (1, 2, 3, 4, 5)
    return {
        m: _subjective_count(db_path, m, chapters, usable_only=usable_only) for m in bands
    }


def _fill_slots_from_supply(need: int, slot_marks: int, pool: dict[int, int]) -> int:
    """Return how many of `need` slots can be filled; mutates pool."""
    filled = 0
    for band in subjective_marks_fallback(slot_marks):
        available = pool.get(band, 0)
        if available <= 0:
            continue
        take = min(need - filled, available)
        pool[band] = available - take
        filled += take
        if filled >= need:
            break
    return filled


def can_fill_spread(
    db_path: Path,
    counts: SectionCounts,
    chapters: list[str] | None,
    supply: dict[int, int] | None = None,
) -> bool:
    pool = dict(supply if supply is not None else subjective_supply(db_path, chapters))
    seeds = _mcq_seed_count(db_path, chapters)
    if counts.one > 0 and seeds < 1:
        return False
    slots = (
        (counts.vsa, 2),
        (counts.sa, 3),
        (counts.case, 4),
        (counts.la, 5),
    )
    for need, mark_value in slots:
        if need <= 0:
            continue
        if _fill_slots_from_supply(need, mark_value, pool) < need:
            return False
    return True


def max_feasible_targets(
    db_path: Path,
    chapters: list[str] | None,
    candidates: tuple[int, ...] | None = None,
) -> tuple[int, list[int]]:
    """Highest feasible target marks and all feasible values from candidates (descending scan)."""
    opts = list(candidates or PAPER_MARKS_CANDIDATES)
    supply = subjective_supply(db_path, chapters)
    allowed: list[int] = []
    for t in sorted(opts, reverse=True):
        planned = cbse_spread_for_total(t)
        counts, _ = rebalance_counts_for_corpus(db_path, planned, chapters)
        if can_fill_spread(db_path, counts, chapters, dict(supply)):
            allowed.append(t)
    allowed.sort()
    max_m = max(allowed) if allowed else 0
    return max_m, allowed


def subjective_marks_fallback(slot_marks: int) -> list[int]:
    """Try exact board marks first, then nearest bands present in many papers."""
    order = {
        4: [4, 3, 5, 2],
        3: [3, 2, 5, 4],
        2: [2, 3, 1],
        5: [5, 3, 2],
    }
    return order.get(slot_marks, [slot_marks])
