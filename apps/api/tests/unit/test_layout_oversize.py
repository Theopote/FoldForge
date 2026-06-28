"""Layout engine must not scale individual papercraft pieces."""

from __future__ import annotations

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.layout_engine import (
    MARGIN_MM,
    PAPER_SIZES_MM,
    detect_layout_issues,
    layout_pieces,
    piece_bounds,
)


def _oversize_piece(width_mm: float, height_mm: float, label: str = "XL") -> UnfoldPiece:
    return UnfoldPiece(
        id="oversize-test",
        face_ids=[0],
        label=label,
        polygon=[
            Point2D(0, 0),
            Point2D(width_mm, 0),
            Point2D(width_mm, height_mm),
            Point2D(0, height_mm),
        ],
    )


def test_oversize_piece_is_not_scaled() -> None:
    page_w, page_h = PAPER_SIZES_MM[PaperSize.A4]
    usable_w = page_w - 2 * MARGIN_MM
    usable_h = page_h - 2 * MARGIN_MM
    piece = _oversize_piece(usable_w + 40, usable_h + 20, label="Panel A")
    source_bounds = piece_bounds(piece, include_tabs=True)

    pages = layout_pieces([piece], PaperSize.A4)
    issues = detect_layout_issues(pages)

    placed = pages[0].placed_pieces[0].piece
    placed_bounds = piece_bounds(placed, include_tabs=True)

    source_w = source_bounds[2] - source_bounds[0]
    source_h = source_bounds[3] - source_bounds[1]
    placed_w = placed_bounds[2] - placed_bounds[0]
    placed_h = placed_bounds[3] - placed_bounds[1]

    assert abs(placed_w - source_w) < 0.01
    assert abs(placed_h - source_h) < 0.01
    assert "-scaled" not in placed.id
    assert issues.oversize_piece_labels == ["Panel A"]
    assert issues.overflow_count == 1
