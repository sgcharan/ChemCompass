from pyq_llm.validate_mcq import validate_mcq_payload


def test_valid_mcq():
    data = {
        "text": "Which colligative property is used to determine molar mass of polymers?",
        "options": ["Osmotic pressure", "Boiling point", "Vapour pressure", "Surface tension"],
        "answer": "Osmotic pressure",
    }
    ok, errs = validate_mcq_payload(data)
    assert ok and not errs


def test_invalid_options():
    data = {
        "text": "What is the hybridisation of carbon in ethene?",
        "options": ["sp", "sp", "sp3", "sp2"],
        "answer": "sp2",
    }
    ok, errs = validate_mcq_payload(data)
    assert not ok


def test_rejects_lazy_distractors():
    data = {
        "text": "Which property depends only on the number of solute particles?",
        "options": [
            "Osmotic pressure",
            "None of these",
            "All of these",
            "Cannot be determined",
        ],
        "answer": "Osmotic pressure",
    }
    ok, errs = validate_mcq_payload(data)
    assert not ok
