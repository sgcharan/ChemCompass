from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pyq_llm.subjective_quality import is_good_subjective_text


@dataclass
class PyqHit:
    id: str
    paper_id: str
    number: int
    marks: int | None
    text: str
    answer: str
    chapter: str | None
    score: float


def _tokenize(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{3,}", q.lower()) if t not in {"the", "and", "for", "with"}]


def retrieve(
    db_path: Path,
    *,
    chapter: str | None = None,
    query: str | None = None,
    marks: int | None = None,
    limit: int = 5,
    exclude_ids: set[str] | None = None,
) -> list[PyqHit]:
    exclude_ids = exclude_ids or set()
    if not db_path.is_file():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    hits: list[PyqHit] = []

    if query and query.strip():
        tokens = _tokenize(query)[:10]
        fts_q = " OR ".join(tokens) if tokens else query.replace('"', "")
        try:
            cur = conn.execute(
                """
                SELECT q.id, q.paper_id, q.number, q.marks, q.text, q.answer, q.chapter,
                       bm25(questions_fts) AS score
                FROM questions_fts
                JOIN questions q ON q.id = questions_fts.id
                WHERE questions_fts MATCH ?
                  AND q.usable = 1
                  AND (? IS NULL OR q.chapter = ?)
                ORDER BY score
                LIMIT ?
                """,
                (fts_q, chapter, chapter, limit * 3),
            )
            for row in cur:
                if row["id"] in exclude_ids:
                    continue
                if marks is not None and row["marks"] != marks:
                    continue
                hits.append(
                    PyqHit(
                        id=row["id"],
                        paper_id=row["paper_id"],
                        number=row["number"],
                        marks=row["marks"],
                        text=row["text"],
                        answer=row["answer"],
                        chapter=row["chapter"],
                        score=float(row["score"] or 0),
                    )
                )
                if len(hits) >= limit:
                    break
        except sqlite3.OperationalError:
            pass

    if len(hits) < limit:
        sql = """
            SELECT id, paper_id, number, marks, text, answer, chapter
            FROM questions WHERE usable = 1
        """
        params: list[object] = []
        if chapter:
            sql += " AND chapter = ?"
            params.append(chapter)
        if marks is not None:
            sql += " AND marks = ?"
            params.append(marks)
        sql += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit - len(hits))
        cur = conn.execute(sql, params)
        seen = {h.id for h in hits}
        for row in cur:
            if row["id"] in seen or row["id"] in exclude_ids:
                continue
            hits.append(
                PyqHit(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    number=row["number"],
                    marks=row["marks"],
                    text=row["text"],
                    answer=row["answer"],
                    chapter=row["chapter"],
                    score=0.0,
                )
            )

    conn.close()
    return hits[:limit]


def list_mcq_seed_pool(
    db_path: Path,
    *,
    chapters: list[str] | None = None,
    exclude_ids: set[str] | None = None,
    limit: int = 80,
) -> list[PyqHit]:
    """PYQ rows for LLM MCQ generation (relaxed marks / usable flags)."""
    from pyq_llm.answer_quality import filter_quality_hits

    exclude_ids = exclude_ids or set()
    pool: list[PyqHit] = []
    seen: set[str] = set()

    def _pull(marks: int | None, usable_only: bool, take: int) -> None:
        nonlocal pool
        if len(pool) >= limit:
            return
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT id, paper_id, number, marks, text, answer, chapter
            FROM questions
            WHERE length(trim(text)) >= 18
              AND length(trim(coalesce(answer, ''))) >= 1
        """
        params: list[object] = []
        if usable_only:
            sql += " AND usable = 1"
        if marks is not None:
            sql += " AND marks = ?"
            params.append(marks)
        else:
            sql += " AND marks IN (1, 2, 3)"
        if chapters:
            placeholders = ",".join("?" * len(chapters))
            sql += f" AND chapter IN ({placeholders})"
            params.extend(chapters)
        sql += " ORDER BY RANDOM() LIMIT ?"
        params.append(take)
        for row in conn.execute(sql, params):
            if row["id"] in exclude_ids or row["id"] in seen:
                continue
            hit = PyqHit(
                id=row["id"],
                paper_id=row["paper_id"],
                number=row["number"],
                marks=row["marks"],
                text=row["text"],
                answer=row["answer"] or "",
                chapter=row["chapter"],
                score=0.0,
            )
            seen.add(hit.id)
            pool.append(hit)
            if len(pool) >= limit:
                break
        conn.close()

    for marks in (1, 2, None):
        for usable_only in (True, False):
            _pull(marks, usable_only, limit)
            pool = filter_quality_hits(pool)
            if len(pool) >= limit:
                return pool[:limit]

    return filter_quality_hits(pool)[:limit]


def sample_by_marks(
    db_path: Path,
    *,
    marks: int,
    count: int,
    chapters: list[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[PyqHit]:
    """Random PYQ rows with given board marks (prefer usable corpus rows)."""
    exclude_ids = exclude_ids or set()
    if not db_path.is_file() or count <= 0:
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    def _fetch(usable_only: bool) -> list[PyqHit]:
        sql = """
            SELECT id, paper_id, number, marks, text, answer, chapter
            FROM questions
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
        sql += " ORDER BY RANDOM() LIMIT ?"
        params.append(count * 4)
        cur = conn.execute(sql, params)
        out: list[PyqHit] = []
        for row in cur:
            if row["id"] in exclude_ids:
                continue
            hit = PyqHit(
                id=row["id"],
                paper_id=row["paper_id"],
                number=row["number"],
                marks=row["marks"],
                text=row["text"],
                answer=row["answer"] or "",
                chapter=row["chapter"],
                score=0.0,
            )
            if not is_good_subjective_text(hit.text, marks=marks):
                continue
            out.append(hit)
            if len(out) >= count:
                break
        return out

    hits = _fetch(True)
    if len(hits) < count:
        seen = {h.id for h in hits}
        for h in _fetch(False):
            if h.id in seen:
                continue
            hits.append(h)
            seen.add(h.id)
            if len(hits) >= count:
                break

    conn.close()
    return hits[:count]


def sample_for_slot(
    db_path: Path,
    *,
    slot_marks: int,
    count: int,
    chapters: list[str] | None = None,
    exclude_ids: set[str] | None = None,
    fallback_marks: list[int] | None = None,
) -> list[PyqHit]:
    """Sample subjective questions for a paper slot, trying alternate mark bands if needed."""
    from pyq_llm.corpus_spread import subjective_marks_fallback

    exclude_ids = exclude_ids or set()
    order = fallback_marks if fallback_marks is not None else subjective_marks_fallback(slot_marks)
    out: list[PyqHit] = []
    for band in order:
        if len(out) >= count:
            break
        need = count - len(out)
        batch = sample_by_marks(
            db_path,
            marks=band,
            count=need,
            chapters=chapters,
            exclude_ids=exclude_ids | {h.id for h in out},
        )
        for h in batch:
            if not is_good_subjective_text(h.text, marks=slot_marks if band == slot_marks else band):
                continue
            out.append(h)
            if len(out) >= count:
                break
    return out[:count]
