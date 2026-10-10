"""Display formatting: HTML sub/sup → Unicode for chemistry."""

from __future__ import annotations

import re

_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUP = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def format_question_layout(text: str) -> str:
    """Line breaks for (i)/(ii) sub-parts and separate board questions."""
    out = format_chemistry_display(text)
    out = re.sub(
        r"([^\n])\s*\((i{1,3}|iv|v|vi{0,3}|ix|x)\)\s*",
        r"\1\n(\2) ",
        out,
        flags=re.I,
    )
    out = re.sub(
        r"(\?)\s*\n\s*((?:How many|Define|Assuming|Calculate|What is|Write the|Draw the)\b)",
        r"\1\n\n\2",
        out,
        flags=re.I,
    )
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def format_chemistry_display(text: str) -> str:
    if not text:
        return text
    out = text
    out = re.sub(
        r"<sub>\s*([^<]+?)\s*</sub>",
        lambda m: m.group(1).translate(_SUB),
        out,
        flags=re.I,
    )
    out = re.sub(
        r"<sup>\s*([^<]+?)\s*</sup>",
        lambda m: m.group(1).translate(_SUP),
        out,
        flags=re.I,
    )
    out = re.sub(r"</?sub>", "", out, flags=re.I)
    out = re.sub(r"</?sup>", "", out, flags=re.I)
    return out


def format_mcq_fields(data: dict) -> dict:
    for key in ("text", "answer", "explanation", "basedOnStem", "basedOnMarkingAnswer"):
        if key in data and data[key]:
            data[key] = format_chemistry_display(str(data[key]))
    if data.get("options"):
        data["options"] = [format_chemistry_display(str(o)) for o in data["options"]]
    return data
