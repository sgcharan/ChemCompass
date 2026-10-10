from pyq_llm.answer_quality import is_garbled_answer, is_good_option
from pyq_llm.retrieve import PyqHit


def test_garbled_formula_answers():
    assert is_garbled_answer('022x1023 x(4x10-8)3')
    assert is_garbled_answer('866x10-8 ! ".#"$%')
    assert not is_garbled_answer("Due to incomplete filling of d-orbitals")


def test_lazy_options_rejected():
    assert not is_good_option("None of these")
    assert not is_good_option("All of these")
    assert is_good_option("Elevation of boiling point is a colligative property")


def test_hit_filter():
    from pyq_llm.answer_quality import filter_quality_hits, is_good_pyq_hit

    good = PyqHit(
        id="a:1",
        paper_id="a",
        number=1,
        marks=1,
        text="What is meant by an ideal solution?",
        answer="A solution that obeys Raoult's law over the entire range of concentration.",
        chapter="Solutions",
        score=0,
    )
    bad = PyqHit(
        id="b:2",
        paper_id="b",
        number=2,
        marks=1,
        text="866x10-8",
        answer="866x10-8 !",
        chapter="Solutions",
        score=0,
    )
    assert is_good_pyq_hit(good)
    assert not is_good_pyq_hit(bad)
    assert len(filter_quality_hits([bad, good])) == 1
