from pyq_llm.generate_mcq import resolve_stem_mode


def test_resolve_mix_alternates():
    assert resolve_stem_mode("mix", 0) == "strict"
    assert resolve_stem_mode("mix", 1) == "creative"
    assert resolve_stem_mode("mix", 2) == "strict"


def test_resolve_fixed():
    assert resolve_stem_mode("strict", 5) == "strict"
    assert resolve_stem_mode("creative", 5) == "creative"
