"""Unit tests for PDF font helpers."""

from __future__ import annotations

from app.services.pdf_fonts import contains_cjk, wrap_instruction_line


def test_contains_cjk_detects_chinese() -> None:
    assert contains_cjk("中文提示")
    assert not contains_cjk("English only")


def test_wrap_instruction_line_splits_long_cjk_without_spaces() -> None:
    lines = wrap_instruction_line(
        "这是一段没有空格的中文说明文字需要按字符换行",
        "Helvetica",
        9,
        40,
    )

    assert len(lines) > 1
    assert "".join(lines) == "这是一段没有空格的中文说明文字需要按字符换行"
