"""Filter English lines: allowlist charset + English/chemistry signals."""

from __future__ import annotations

import re

from pyq_extract.lines import TextLine

DEVANAGARI_THRESHOLD = 0.12
CHARSET_MIN_RATIO = 0.92

NOISE_PATTERNS = (
    re.compile(r"P\.T\.O\.", re.I),
    re.compile(r"^--\s*\d+\s+of\s+\d+\s*--", re.I),
    re.compile(r"^56[/\\]"),
    re.compile(r"^56tU", re.I),
)

# Chemistry / math symbols often seen in CBSE PDFs (beyond basic ASCII punctuation)
_EXTRA_ALLOWED = "→←≥≤±×·•½³²⁺⁻₀₁₂₃₄₅₆₇₈₉Δ∆"

_EN_WORDS = re.compile(
    r"\b(the|of|and|to|in|is|are|which|what|give|write|define|calculate|complete|draw|"
    r"arrange|examine|following|reaction|compound|solution|each|why|how|from|with|for|"
    r"between|into|one|two|three|account|outline|name|type|stable|employed|example|"
    r"ideal|differences|principles|products|distinguish|increasing|order|molar|mass|"
    r"element|crystal|defect|density|benzene|freezing|water|starch|emulsion|volatile|"
    r"isotonic|solubility|ore|copper|agent|reducing|leached|grade|low|high|acid|base|"
    r"or\b|given|state|explain|describe|identify|prepare|show|find|using|when|where|"
    r"both|than|that|this|these|those|not|can|may|will|has|have|been|was|were|does|did)\b",
    re.I,
)

_CHEM = re.compile(
    r"(\[Co|\[Cr|NH3|NaOH|H2SO|IUPAC|SN1|SN2|→|->|mol-?l|g/cm|f\.c\.c|Δ|∆|CHO|COOH|C6H|Cl2|SO2)",
    re.I,
)

_QUESTION_START = re.compile(r"^\d{1,2}\.\s*$")


def _is_allowed_char(ch: str) -> bool:
    if ch.isspace():
        return True
    if "\u0900" <= ch <= "\u097F":
        return False
    if ch.isascii() and (ch.isalnum() or ch in ".,;:'\"?!@#%&()[]{}+-=/_\\|^~`<>*"):
        return True
    if ch in _EXTRA_ALLOWED:
        return True
    return False


def charset_allow_ratio(text: str) -> float:
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    ok = sum(1 for c in chars if _is_allowed_char(c))
    return ok / len(chars)


def is_noise_line(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(t):
            return True
    if _QUESTION_START.match(t):
        return True
    if re.match(r"^\d{1,2}$", t):
        return True
    return False


def _garbled_latin_hindi(text: str) -> bool:
    """Hindi lines often appear as Latin OCR with heavy punctuation, no real English."""
    t = text.strip()
    if len(t) < 12:
        return False
    if _EN_WORDS.search(t) or _CHEM.search(t):
        return False
    if " " not in t and len(t) > 18:
        return True
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return False
    weird = sum(1 for c in t if c in "{}*'+\\|")
    if weird / max(len(t), 1) > 0.06:
        return True
    vowel_ratio = sum(1 for c in "".join(letters).lower() if c in "aeiou") / len(letters)
    if len(letters) > 15 and vowel_ratio < 0.18:
        return True
    return False


def has_english_or_chemistry_signal(text: str) -> bool:
    t = text.strip()
    if _CHEM.search(t):
        return True
    if _EN_WORDS.search(t):
        return True
    if re.match(r"^[\(\[]?[ivx]+\)", t, re.I):
        return True
    if re.match(r"^\([a-z]\)", t, re.I):
        return True
    if re.match(r"^OR\s*\.?\s*$", t, re.I):
        return True
    if re.match(r"^[\d\+\-\s\[\]\(\)→\->=\./A-Za-z°]+$", t) and re.search(r"\d", t):
        if sum(1 for c in t if c.isalpha()) >= 2:
            return True
    return False


def is_english_continuation(text: str) -> bool:
    """Short tail of a sentence (e.g. 'ore ?') after a kept English line."""
    t = text.strip()
    if not t or len(t) > 40:
        return False
    if charset_allow_ratio(t) < CHARSET_MIN_RATIO:
        return False
    letters = sum(1 for c in t if c.isalpha())
    if letters < 1:
        return False
    if re.match(r"^[A-Za-z][A-Za-z?.,'\s-]*$", t):
        return True
    return False


def is_english_content(line: TextLine) -> bool:
    t = line.text.strip()
    if is_noise_line(t):
        return False
    if line.devanagari_ratio > DEVANAGARI_THRESHOLD:
        return False
    if charset_allow_ratio(t) < CHARSET_MIN_RATIO:
        return False
    if _garbled_latin_hindi(t):
        return False
    return has_english_or_chemistry_signal(t)


def filter_block_to_english(lines: list[TextLine]) -> list[TextLine]:
    out: list[TextLine] = []
    for line in lines:
        if is_english_content(line):
            out.append(line)
        elif out and is_english_continuation(line.text):
            out.append(line)
    return out


def general_instructions_text(lines: list[TextLine]) -> str:
    chunks: list[str] = []
    collecting = False
    for line in lines:
        if re.search(r"General\s+Instructions", line.text, re.I):
            collecting = True
        if collecting:
            chunks.append(line.text)
            if re.search(r"calculators\s+is\s+not\s+allowed", line.text, re.I):
                break
    return "\n".join(chunks)
