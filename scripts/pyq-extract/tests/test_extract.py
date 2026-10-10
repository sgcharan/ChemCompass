"""Golden tests on the 2014 Delhi sample PDF."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyq_extract.extract import extract_paper

DEFAULT_SAMPLE = Path(
    r"C:\Users\sgcha\OneDrive\Documents\ChemCompass\CBSE\PYQs\Chemistry\chemistry-2014-main-exams-delhi-set-1.pdf"
)


def sample_pdf() -> Path:
    override = os.environ.get("PYQ_SAMPLE_PDF")
    if override:
        return Path(override)
    return DEFAULT_SAMPLE


@pytest.fixture(scope="module")
def paper(tmp_path_factory):
    pdf = sample_pdf()
    if not pdf.is_file():
        pytest.skip(f"Sample PDF not found: {pdf}")
    out = tmp_path_factory.mktemp("pyq_out")
    return extract_paper(pdf, output_dir=out, write_markdown=True)


def test_thirty_questions(paper):
    assert len(paper["questions"]) == 30
    assert paper["validation"]["ok"] is True


def test_rubric_ranges(paper):
    rubric = paper["rubric"]
    assert rubric.get("1-8") == 1
    assert rubric.get("9-18") == 2
    assert rubric.get("19-27") == 3
    assert rubric.get("28-30") == 5


def test_q1_content(paper):
    q1 = next(q for q in paper["questions"] if q["number"] == 1)
    assert "oil in water" in q1["text"].lower()
    assert "water in oil" in q1["text"].lower()
    assert "emulsion" in q1["text"].lower()
    assert "milk" in q1["answer"].lower() or "vanishing cream" in q1["answer"].lower()
    assert q1["marks"] == 1


def test_q7_compound_formulas(paper):
    q7 = next(q for q in paper["questions"] if q["number"] == 7)
    t = q7["text"]
    assert "C6H5NH2" in t
    assert "(C2H5)2NH" in t
    assert "C2H5NH2" in t
    assert "C2H,2NH" not in t
    assert "c6HsNH2" not in t


def test_q8_starch_only(paper):
    q8 = next(q for q in paper["questions"] if q["number"] == 8)
    t = q8["text"].lower()
    assert "starch" in t and "water soluble" in t
    assert "f.c.c" not in t and "atomic mass" not in t


def test_q9_fcc_setup(paper):
    q9 = next(q for q in paper["questions"] if q["number"] == 9)
    t = q9["text"].lower()
    assert "atomic mass" in t
    assert "f.c.c" in t or "lattice" in t
    assert "density" in t or "g/cm" in t


def test_q3_starts_at_english(paper):
    q3 = next(q for q in paper["questions"] if q["number"] == 3)
    assert q3["text"].strip().lower().startswith("which")
    assert "[co(nh" not in q3["text"].lower().split("which")[0]


def test_q15_chemistry_content(paper):
    q15 = next(q for q in paper["questions"] if q["number"] == 15)
    blob = (q15.get("text") or "") + (q15.get("answer") or "")
    assert "chemical equations" in blob.lower() or "H2SO" in blob or "HI <" in blob
    assert q15.get("answerMarks")


def test_segmentation_metadata(paper):
    assert paper["id"] == "pyq-2014-main-delhi-set-1"
    assert paper["source"]["year"] == 2014
