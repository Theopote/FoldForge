"""Page sizing helpers for instruction PDF exports."""

from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from app.schemas.model import ProjectSettings
from app.services.layout_engine import PAPER_SIZES_MM


def instruction_page_size(settings: ProjectSettings | None = None) -> tuple[float, float]:
    """Match instruction booklet page size to the project's paper setting."""
    if settings is None:
        return A4
    width_mm, height_mm = PAPER_SIZES_MM[settings.paper_size]
    return (width_mm * mm, height_mm * mm)
