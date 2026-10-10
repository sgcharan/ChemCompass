from pyq_llm.mark_spread import cbse_spread_for_total, marks_from_counts


def test_seventy():
    c = cbse_spread_for_total(70)
    assert marks_from_counts(c) == 70
    assert c.one == 16 and c.vsa == 5


def test_thirty():
    c = cbse_spread_for_total(30)
    assert marks_from_counts(c) == 30
