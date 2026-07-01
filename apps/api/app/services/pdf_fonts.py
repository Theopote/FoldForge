"""Font helpers for ReportLab PDF exports (Latin + optional CJK)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

CJK_FONT_NAME = "FoldForgeCJK"
_CJK_REGISTERED = False


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def register_instruction_pdf_fonts() -> bool:
    """Register a system CJK font when available. Returns True on success."""
    global _CJK_REGISTERED
    if _CJK_REGISTERED or CJK_FONT_NAME in pdfmetrics.getRegisteredFontNames():
        _CJK_REGISTERED = True
        return True

    for path in _cjk_font_candidates():
        if not path.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont(CJK_FONT_NAME, str(path)))
            _CJK_REGISTERED = True
            return True
        except Exception:
            continue
    return False


def instruction_font_for(text: str, *, weight: str = "regular") -> str:
    """Pick a font that can render the given text."""
    if register_instruction_pdf_fonts() and contains_cjk(text):
        return CJK_FONT_NAME
    if weight == "bold":
        return "Helvetica-Bold"
    if weight == "italic":
        return "Helvetica-Oblique"
    return "Helvetica"


def wrap_instruction_line(
    text: str,
    font_name: str,
    font_size: int,
    max_width: float,
) -> list[str]:
    """Wrap a single line of instruction text to fit the printable width."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    if not text:
        return [""]

    if contains_cjk(text) or font_name == CJK_FONT_NAME:
        lines: list[str] = []
        current = ""
        for char in text:
            candidate = f"{current}{char}"
            if stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines or [""]

    words = text.split()
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _cjk_font_candidates() -> list[Path]:
    candidates: list[Path] = []
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        candidates.extend(
            [
                windir / "Fonts" / "msyh.ttc",
                windir / "Fonts" / "msyhbd.ttc",
                windir / "Fonts" / "simsun.ttc",
                windir / "Fonts" / "simhei.ttf",
            ]
        )
    elif sys.platform == "darwin":
        candidates.extend(
            [
                Path("/System/Library/Fonts/PingFang.ttc"),
                Path("/System/Library/Fonts/STHeiti Light.ttc"),
                Path("/Library/Fonts/Arial Unicode.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
                Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            ]
        )
    return candidates
