"""Instruction PDF layout helpers."""

from __future__ import annotations

from reportlab.lib.pagesizes import A3, A4, letter
from reportlab.lib.units import mm

from app.schemas.model import PaperSize, ProjectSettings
from app.services.instruction_pdf_layout import instruction_page_size


def test_instruction_page_size_defaults_to_a4() -> None:
    width, height = instruction_page_size()
    assert abs(width - A4[0]) < 1
    assert abs(height - A4[1]) < 1


def test_instruction_page_size_matches_project_paper() -> None:
    a3 = instruction_page_size(ProjectSettings(paper_size=PaperSize.A3))
    assert abs(a3[0] - A3[0]) < 1
    assert abs(a3[1] - A3[1]) < 1

    letter_size = instruction_page_size(ProjectSettings(paper_size=PaperSize.LETTER))
    assert abs(letter_size[0] - letter[0]) < 1
    assert abs(letter_size[1] - letter[1]) < 1

    custom = instruction_page_size(ProjectSettings(paper_size=PaperSize.A4))
    assert abs(custom[0] - 210 * mm) < 1
