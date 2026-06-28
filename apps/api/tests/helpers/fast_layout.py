"""Fast row layout for pipeline tests — delegates to production shelf packer."""

from __future__ import annotations

from app.models.geometry import UnfoldPiece
from app.schemas.model import PaperSize
from app.services.cancel import CancelCheck
from app.services.layout_engine import LayoutPlacementResult, layout_pieces_shelf


def layout_pieces_row(
    pieces: list[UnfoldPiece],
    paper_size: PaperSize,
    gap_mm: float = 8.0,
    cancel_check: CancelCheck | None = None,
) -> LayoutPlacementResult:
    """Place pieces with shelf scanning (test helper alias)."""
    return layout_pieces_shelf(
        pieces,
        paper_size,
        gap_mm=gap_mm,
        cancel_check=cancel_check,
    )
