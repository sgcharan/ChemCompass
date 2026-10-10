from pyq_llm.validate_subjective import validate_subjective_payload


def test_strict_stem_match():
    stem = "Define molality."
    data = {"text": stem, "answer": "Molality is moles of solute per kg solvent."}
    ok, errs = validate_subjective_payload(data, slot_marks=2, strict_stem=stem)
    assert ok and not errs


def test_strict_stem_mismatch():
    data = {"text": "Wrong question?", "answer": "answer here enough"}
    ok, errs = validate_subjective_payload(
        data, slot_marks=2, strict_stem="Define molality."
    )
    assert not ok
    assert any("mismatch" in e for e in errs)
