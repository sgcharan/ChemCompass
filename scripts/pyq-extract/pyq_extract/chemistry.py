"""Chemistry-aware OCR / font glitch normalization."""

from __future__ import annotations

import re

_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bHr\b"), "H2"),
    (re.compile(r"\bHrO\b", re.I), "H2O"),
    (re.compile(r"SOo", re.I), "SO4"),
    (re.compile(r"SO_?o", re.I), "SO4"),
    (re.compile(r"HrSO"), "H2SO"),
    (re.compile(r"mnrks", re.I), "marks"),
    (re.compile(r"C\\Pz", re.I), "Ca3P2"),
    (re.compile(r"C\\P_?2", re.I), "Ca3P2"),
    (re.compile(r"cl2lP", re.I), "Cl2/P"),
    (re.compile(r"cl2tP", re.I), "Cl2/P"),
    (re.compile(r"gcm-?3", re.I), "g/cm3"),
    (re.compile(r"mol-?l", re.I), "mol-1"),
    (re.compile(r"S\*2", re.I), "SN2"),
    (re.compile(r"S\*1", re.I), "SN1"),
    (re.compile(r"equarion", re.I), "equation"),
    (re.compile(r"hopanone", re.I), "propanone"),
    (re.compile(r"Wolff-Kishnerreduction", re.I), "Wolff-Kishner reduction"),
    (re.compile(r"Aldolcondensation", re.I), "Aldol condensation"),
    (re.compile(r"Cannizzaroreaction", re.I), "Cannizzaro reaction"),
    (re.compile(r"cHr", re.I), "CH"),
    (re.compile(r"€"), "C"),
    (re.compile(r"\bc6HsNH2\b", re.I), "C6H5NH2"),
    (re.compile(r"\(C2H,\s*2NH", re.I), "(C2H5)2NH"),
    (re.compile(r"\(c2Hr2NH\b", re.I), "(C2H5)2NH"),
    (re.compile(r"C2H,2NH", re.I), "(C2H5)2NH"),
]

_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUPERSCRIPT_DIGITS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def _normalize_compound_list_line(text: str) -> str:
    """Fix comma-separated amine lists (e.g. Q7 solubility)."""
    if not re.search(r"NH2|NH3", text, re.I):
        return text
    out = text
    out = re.sub(
        r"(C6H5NH2,\s*)(?:\(C2H5\)2NH|C2H,2NH|\(C2H,2NH)",
        r"\1(C2H5)2NH",
        out,
        flags=re.I,
    )
    out = re.sub(r",\s*\(C2H5\)2NH\s*,", ", (C2H5)2NH,", out, flags=re.I)
    return out


def normalize_chemistry_text(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern, repl in _REPLACEMENTS:
        out = pattern.sub(repl, out)
    out = re.sub(r"\s+->\s*", " → ", out)
    out = re.sub(r"\s*--+\s*", " → ", out)
    lines = [_normalize_compound_list_line(ln) for ln in out.splitlines()]
    return "\n".join(lines).strip()


def spans_to_text_with_scripts(page_dict: dict) -> str:
    """Rebuild text from pymupdf dict spans using superscript/subscript flags when present."""
    parts: list[str] = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_parts: list[str] = []
            for span in line.get("spans", []):
                t = span.get("text", "")
                flags = span.get("flags", 0)
                if flags & 2**4:
                    t = t.translate(_SUPERSCRIPT_DIGITS)
                elif flags & 2**5:
                    t = t.translate(_SUBSCRIPT_DIGITS)
                line_parts.append(t)
            if line_parts:
                parts.append("".join(line_parts))
    return "\n".join(parts)
