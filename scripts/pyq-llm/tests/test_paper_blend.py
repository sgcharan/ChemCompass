from pyq_llm.mark_spread import cbse_spread_for_total
from pyq_llm.paper_blend import build_slot_list, plan_slot_modes


def test_build_slots_30_marks():
    counts = cbse_spread_for_total(30)
    slots = build_slot_list(counts)
    assert len(slots) == counts.one + counts.vsa + counts.sa + counts.case + counts.la


def test_plan_zero_all_corpus():
    counts = cbse_spread_for_total(30)
    slots = plan_slot_modes(build_slot_list(counts), 0)
    assert all(s.mode == "corpus" for s in slots)


def test_plan_100_all_llm():
    counts = cbse_spread_for_total(30)
    slots = plan_slot_modes(build_slot_list(counts), 100)
    assert all(s.mode == "llm" for s in slots)


def test_plan_50_mixed():
    counts = cbse_spread_for_total(30)
    slots = plan_slot_modes(build_slot_list(counts), 50)
    n_llm = sum(1 for s in slots if s.mode == "llm")
    assert 0 < n_llm < len(slots)
