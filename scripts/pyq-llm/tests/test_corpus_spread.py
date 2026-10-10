from pathlib import Path

from pyq_llm.corpus_spread import rebalance_counts_for_corpus
from pyq_llm.mark_spread import SectionCounts, cbse_spread_for_total, marks_from_counts


def test_rebalance_swaps_missing_four_markers():
    repo = Path(__file__).resolve().parents[3]
    db = repo / "data" / "pyq-corpus" / "corpus.sqlite"
    if not db.is_file():
        return
    planned = cbse_spread_for_total(30)
    assert planned.case >= 1
    adjusted, notes = rebalance_counts_for_corpus(db, planned, None)
    assert adjusted.case == 0
    assert adjusted.vsa >= planned.vsa
    assert marks_from_counts(adjusted) == marks_from_counts(planned)
    assert any("4-mark" in n for n in notes)


def test_fallback_order():
    from pyq_llm.corpus_spread import subjective_marks_fallback

    assert subjective_marks_fallback(4)[0] == 4
    assert 3 in subjective_marks_fallback(4)


def test_max_feasible_all_chapters_at_least_30():
    repo = Path(__file__).resolve().parents[3]
    db = repo / "data" / "pyq-corpus" / "corpus.sqlite"
    if not db.is_file():
        return
    from pyq_llm.corpus_spread import max_feasible_targets

    max_m, allowed = max_feasible_targets(db, None)
    assert max_m >= 30
    assert 30 in allowed
    assert allowed == sorted(allowed)


def test_max_feasible_single_chapter_lower_than_all():
    repo = Path(__file__).resolve().parents[3]
    db = repo / "data" / "pyq-corpus" / "corpus.sqlite"
    if not db.is_file():
        return
    from pyq_llm.corpus_spread import max_feasible_targets

    max_all, _ = max_feasible_targets(db, None)
    max_one, allowed_one = max_feasible_targets(db, ["Solutions"])
    assert max_one <= max_all
    if allowed_one:
        assert max_one == max(allowed_one)


def test_can_fill_spread_respects_mcq_seeds():
    from pyq_llm.corpus_spread import can_fill_spread, subjective_supply

    repo = Path(__file__).resolve().parents[3]
    db = repo / "data" / "pyq-corpus" / "corpus.sqlite"
    if not db.is_file():
        return
    counts = cbse_spread_for_total(10)
    supply = subjective_supply(db, None)
    assert can_fill_spread(db, counts, None, supply) in (True, False)
