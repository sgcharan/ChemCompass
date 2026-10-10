"""Unified PYQ corpus: SQLite + JSONL export and quality reports."""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from pyq_extract.extract import extract_paper

CHAPTER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Solutions": ("raoult", "colligative", "molality", "benzene", "freezing point", "azeotrope", "ideal solution"),
    "Electrochemistry": ("cell", "electrode", "nernst", "conductivity", "molar conductivity", "electrolysis", "emf"),
    "Chemical Kinetics": ("order of reaction", "molecularity", "rate constant", "activation energy", "half-life", "catalyst"),
    "d- and f-Block Elements": ("transition", "lanthanoid", "actinoid", "k2cr2o7", "kmno4", "chromate", "d-block"),
    "Coordination Compounds": ("coordination", "ligand", "iupac", "[co", "[cr", "cfse", "isomerism", "werners"),
    "Haloalkanes and Haloarenes": ("sn1", "sn2", "haloalkane", "haloarene", "aryl halide", "grignard"),
    "Alcohols, Phenols and Ethers": ("phenol", "alcohol", "ether", "williamson", "dehydration"),
    "Aldehydes, Ketones and Carboxylic Acids": ("aldehyde", "ketone", "carboxylic", "cannizzaro", "aldol", "tollens"),
    "Amines": ("amine", "aniline", "diazonium", "hinsberg", "carbylamine"),
    "Biomolecules": ("glucose", "fructose", "protein", "enzyme", "starch", "amino acid", "vitamin", "nucleic"),
}


def infer_chapter(text: str, answer: str = "") -> str | None:
    blob = f"{text} {answer}".lower()
    best: str | None = None
    best_score = 0
    for chapter, keys in CHAPTER_KEYWORDS.items():
        score = sum(1 for k in keys if k in blob)
        if score > best_score:
            best_score = score
            best = chapter
    return best if best_score > 0 else None


def question_usable(q: dict[str, Any]) -> bool:
    text = (q.get("text") or "").strip()
    answer = (q.get("answer") or "").strip()
    if len(text) < 12 or len(answer) < 1:
        return False
    flags = q.get("flags") or []
    if "missing_answer" in flags:
        return False
    return True


@dataclass
class CorpusStats:
    papers: int = 0
    questions: int = 0
    usable: int = 0
    flagged: int = 0


SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
  id TEXT PRIMARY KEY,
  year INTEGER,
  exam TEXT,
  region TEXT,
  set_num INTEGER,
  pdf_path TEXT,
  validation_ok INTEGER,
  question_count INTEGER
);

CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY,
  paper_id TEXT NOT NULL,
  number INTEGER NOT NULL,
  marks INTEGER,
  text TEXT NOT NULL,
  answer TEXT,
  or_text TEXT,
  or_answer TEXT,
  chapter TEXT,
  flags TEXT,
  usable INTEGER NOT NULL,
  FOREIGN KEY (paper_id) REFERENCES papers(id)
);

CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_chapter ON questions(chapter);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5(
          id UNINDEXED,
          paper_id UNINDEXED,
          text,
          answer,
          chapter
        )
        """
    )
    return conn


def _upsert_paper(conn: sqlite3.Connection, paper: dict[str, Any]) -> None:
    src = paper.get("source") or {}
    v = paper.get("validation") or {}
    conn.execute(
        """
        INSERT OR REPLACE INTO papers (id, year, exam, region, set_num, pdf_path, validation_ok, question_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper["id"],
            src.get("year"),
            src.get("exam"),
            src.get("region"),
            src.get("set"),
            src.get("pdfPath"),
            1 if v.get("ok") else 0,
            len(paper.get("questions") or []),
        ),
    )


def _upsert_question(conn: sqlite3.Connection, paper_id: str, q: dict[str, Any]) -> None:
    qid = f"{paper_id}:{q['number']}"
    chapter = infer_chapter(q.get("text") or "", q.get("answer") or "")
    flags = q.get("flags") or []
    usable = 1 if question_usable(q) else 0
    conn.execute(
        """
        INSERT OR REPLACE INTO questions
        (id, paper_id, number, marks, text, answer, or_text, or_answer, chapter, flags, usable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qid,
            paper_id,
            q["number"],
            q.get("marks"),
            q.get("text") or "",
            q.get("answer") or "",
            q.get("orText"),
            q.get("orAnswer"),
            chapter,
            json.dumps(flags),
            usable,
        ),
    )
    conn.execute("DELETE FROM questions_fts WHERE id = ?", (qid,))
    conn.execute(
        "INSERT INTO questions_fts (id, paper_id, text, answer, chapter) VALUES (?, ?, ?, ?, ?)",
        (qid, paper_id, q.get("text") or "", q.get("answer") or "", chapter),
    )


def rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM questions_fts")
    conn.execute(
        """
        INSERT INTO questions_fts (id, paper_id, text, answer, chapter)
        SELECT id, paper_id, text, answer, COALESCE(chapter, '') FROM questions
        """
    )


def ingest_paper_dict(conn: sqlite3.Connection, paper: dict[str, Any]) -> CorpusStats:
    stats = CorpusStats(papers=1)
    _upsert_paper(conn, paper)
    for q in paper.get("questions") or []:
        stats.questions += 1
        if question_usable(q):
            stats.usable += 1
        else:
            stats.flagged += 1
        _upsert_question(conn, paper["id"], q)
    return stats


def ingest_json_file(conn: sqlite3.Connection, path: Path) -> CorpusStats:
    paper = json.loads(path.read_text(encoding="utf-8"))
    return ingest_paper_dict(conn, paper)


def batch_extract_and_ingest(
    pdf_dir: Path,
    raw_json_dir: Path,
    db_path: Path,
    *,
    skip_existing: bool = True,
) -> list[dict[str, Any]]:
    pdfs = sorted(pdf_dir.rglob("*.pdf"))
    raw_json_dir.mkdir(parents=True, exist_ok=True)
    conn = init_db(db_path)
    rows: list[dict[str, Any]] = []

    pdf_name_to_json: dict[str, Path] = {}
    for path in raw_json_dir.glob("*.json"):
        try:
            cand = json.loads(path.read_text(encoding="utf-8"))
            src_path = (cand.get("source") or {}).get("pdfPath") or ""
            if src_path:
                pdf_name_to_json[Path(src_path).name] = path
        except (json.JSONDecodeError, OSError):
            continue

    for pdf in pdfs:
        try:
            paper: dict[str, Any] | None = None
            if skip_existing:
                cached = pdf_name_to_json.get(pdf.name)
                if cached and cached.is_file():
                    paper = json.loads(cached.read_text(encoding="utf-8"))
            if paper is None:
                paper = extract_paper(pdf, output_dir=raw_json_dir, write_markdown=False)
                pdf_name_to_json[pdf.name] = raw_json_dir / f"{paper['id']}.json"
            st = ingest_paper_dict(conn, paper)
            conn.commit()
            rows.append(
                {
                    "id": paper["id"],
                    "pdf": str(pdf),
                    "questions": st.questions,
                    "usable": st.usable,
                    "flagged": st.flagged,
                    "pct_usable": round(100 * st.usable / st.questions, 1) if st.questions else 0,
                    "ok": (paper.get("validation") or {}).get("ok", False),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "id": pdf.stem,
                    "pdf": str(pdf),
                    "questions": 0,
                    "usable": 0,
                    "flagged": 0,
                    "pct_usable": 0,
                    "ok": False,
                    "error": str(exc),
                }
            )

    rebuild_fts(conn)
    conn.commit()
    conn.close()
    return rows


def export_jsonl(db_path: Path, out_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM questions WHERE usable = 1 ORDER BY paper_id, number"
    )
    count = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in cur:
            rec = dict(row)
            rec["flags"] = json.loads(rec.get("flags") or "[]")
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    conn.close()
    return count


def write_quality_report(rows: list[dict[str, Any]], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "pdf", "questions", "usable", "flagged", "pct_usable", "ok", "error"]
    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_papers_from_raw(raw_dir: Path, db_path: Path) -> list[dict[str, Any]]:
    conn = init_db(db_path)
    rows: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.json")):
        try:
            st = ingest_json_file(conn, path)
            paper = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "id": paper["id"],
                    "pdf": (paper.get("source") or {}).get("pdfPath", ""),
                    "questions": st.questions,
                    "usable": st.usable,
                    "flagged": st.flagged,
                    "pct_usable": round(100 * st.usable / st.questions, 1) if st.questions else 0,
                    "ok": (paper.get("validation") or {}).get("ok", False),
                }
            )
        except Exception as exc:
            rows.append({"id": path.stem, "questions": 0, "usable": 0, "error": str(exc)})
    rebuild_fts(conn)
    conn.commit()
    conn.close()
    return rows
