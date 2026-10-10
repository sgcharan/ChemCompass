from pyq_llm.chem_format import format_chemistry_display
from pyq_llm.pyq_ref import pyq_id_to_label, primary_stem
from pyq_llm.retrieve import PyqHit


def test_subscript_html():
    assert "H₂O" in format_chemistry_display("H<sub>2</sub>O")


def test_pyq_label():
    assert "2014" in pyq_id_to_label("pyq-2014-main-delhi-set-1:6")
    assert "Q6" in pyq_id_to_label("pyq-2014-main-delhi-set-1:6")


def test_primary_stem():
    h = PyqHit(
        id="x:1",
        paper_id="x",
        number=1,
        marks=1,
        text="What are isotonic solutions ?\n2",
        answer="Solutions having same osmotic pressure",
        chapter="Solutions",
        score=0,
    )
    assert "isotonic" in primary_stem(h).lower()
