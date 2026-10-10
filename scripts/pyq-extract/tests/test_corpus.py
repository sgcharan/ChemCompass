from __future__ import annotations

import json
from pathlib import Path

from pyq_extract.corpus import export_jsonl, infer_chapter, ingest_json_file, init_db, question_usable


def test_infer_chapter_amines():
    assert infer_chapter("Arrange amines C6H5NH2", "C6H5NH2 < C2H5NH2") == "Amines"


def test_question_usable():
    assert question_usable({"text": "Give an example of emulsion.", "answer": "milk", "flags": []})
    assert not question_usable({"text": "short", "answer": "", "flags": ["missing_answer"]})


def test_ingest_sample_json(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "out" / "pyq-2014-main-delhi-set-1.json"
    if not sample.is_file():
        return
    db = tmp_path / "c.sqlite"
    conn = init_db(db)
    ingest_json_file(conn, sample)
    conn.commit()
    n = export_jsonl(db, tmp_path / "out.jsonl")
    assert n > 20
