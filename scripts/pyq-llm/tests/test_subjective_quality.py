from pyq_llm.subjective_quality import is_good_subjective_text, is_merged_subjective_blob

MERGED = """What is van't Hoff factor ? What types of values can it have if in
forming the solution the solute molecules undergo
Dissociation ?
(ii)
Association ?
How many mL of a 0.1 M HCl solution are required to react
completely with 1 g of a mixture of Na2CO3 and NaHCO3
containing equimolar amounts of both ?
Define
Mole fraction
(ii)
Molality
(iii) Raoult's law
Assuming complete dissociation, calculate the expected freezing
point of a solution prepared by dissolving 6.00 g of Glauber's salt."""


def test_detects_merged_blob():
    assert is_merged_subjective_blob(MERGED)


def test_rejects_bad_corpus_row():
    assert not is_good_subjective_text(MERGED, marks=5)


def test_accepts_single_question():
    text = "Define molality. How is it different from molarity? (2 marks)"
    assert is_good_subjective_text(text, marks=2)
