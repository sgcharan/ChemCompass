"""Marking scheme row grouping tests."""

from __future__ import annotations

import pymupdf as fitz

from pyq_extract.lines import lines_from_pages
from pyq_extract.marking import parse_marking_scheme
from pyq_extract.segment import segment_document

PDF = r"C:\Users\sgcha\OneDrive\Documents\ChemCompass\CBSE\PYQs\Chemistry\chemistry-2014-main-exams-delhi-set-1.pdf"


def test_q1_answer_has_both_emulsion_parts():
    doc = fitz.open(PDF)
    sec = segment_document(doc)
    ms = parse_marking_scheme(lines_from_pages(doc, sec.marking_page_indices))
    doc.close()
    a = ms[1].answer.lower()
    assert "oil in water" in a
    assert "water in oil" in a


def test_q2_answer_not_water_in_oil_only():
    doc = fitz.open(PDF)
    sec = segment_document(doc)
    ms = parse_marking_scheme(lines_from_pages(doc, sec.marking_page_indices))
    doc.close()
    a = ms[2].answer.lower()
    assert "hydrogen" in a or "iron" in a
    assert "water in oil" not in a
