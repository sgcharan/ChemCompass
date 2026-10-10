"""Unit tests for English line filter."""

from __future__ import annotations

from pyq_extract.filter_en import (
    CHARSET_MIN_RATIO,
    charset_allow_ratio,
    filter_block_to_english,
    is_english_content,
)
from pyq_extract.lines import TextLine


def _line(text: str, x0: float = 77.0) -> TextLine:
    return TextLine(page_index=1, y0=100.0, x0=x0, text=text)


def test_rejects_garbled_hindi_latin():
    hindi_ocr = "foqfaaWns*qiw*sirg.t*ir{stHfu+Hqiq+ qqq'{*,,srnrq}rfuqrqmrt?"
    assert not is_english_content(_line(hindi_ocr))


def test_keeps_english_q2_lines():
    assert is_english_content(_line("Which reducing agent is employed to get from the low"))
    assert is_english_content(_line("copper leached grade copper", x0=285))


def test_continuation_ore():
    block = [
        _line("copper leached grade copper", x0=285),
        _line("ore ?"),
    ]
    kept = filter_block_to_english(block)
    assert any("ore" in ln.text for ln in kept)


def test_charset_rejects_devanagari():
    t = "कौन सा अपचायक"
    assert charset_allow_ratio(t) < CHARSET_MIN_RATIO
