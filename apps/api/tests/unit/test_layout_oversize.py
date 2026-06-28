"""Layout fit errors — no per-piece scaling."""

from __future__ import annotations

import pytest

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.layout_engine import (
    MARGIN_MM,
    PAPER_SIZES_MM,
    LayoutPlacementResult,
    LayoutResult,
    find_pieces_too_large_for_paper,
    layout_has_complete_placement,
    layout_pieces,
    placed_piece_ids,
)
from app.services.layout_repair import ensure_layout_exportable, layout_with_repair
from app.services.pipeline_errors import LayoutFitError


def _oversize_piece(width_mm: float, height_mm: float, label: str = "A") -> UnfoldPiece:
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


def test_oversize_piece_is_not_scaled_or_placed() -> None:
    page_w, page_h = PAPER_SIZES_MM[PaperSize.A4]
    usable_w = page_w - 2 * MARGIN_MM
    usable_h = page_h - 2 * MARGIN_MM
    piece = _oversize_piece(usable_w + 40, usable_h + 20, label="Panel A")
    source_bounds = piece.polygon[2].x, piece.polygon[2].y

    result = layout_pieces([piece], PaperSize.A4)
    placed_count = sum(len(page.placed_pieces) for page in result.pages)

    assert placed_count == 0
    assert len(result.unplaced_pieces) == 1
    assert source_bounds[0] > usable_w
    assert "-scaled" not in piece.id


def test_piece_too_large_on_a4_fails_with_clear_message() -> None:
    page_w, page_h = PAPER_SIZES_MM[PaperSize.A4]
    usable_w = page_w - 2 * MARGIN_MM
    usable_h = page_h - 2 * MARGIN_MM
    piece = _oversize_piece(usable_w + 30, usable_h + 10, label="A")

    oversize = find_pieces_too_large_for_paper(
        [piece],
        PaperSize.A4,
        target_height_mm=200,
    )
    assert len(oversize) == 1
    assert oversize[0].label == "A"
    assert "A4" in oversize[0].user_message()
    assert "target height" in oversize[0].user_message().lower()

    result = layout_with_repair([piece], PaperSize.A4, target_height_mm=200)
    assert result.export_blocked is True
    assert result.oversize_piece_labels == ["A"]
    assert result.scaled_piece_labels == ["A"]
    assert result.oversize_piece_labels == ["A"]

    with pytest.raises(LayoutFitError) as exc_info:
        ensure_layout_exportable(result)

    assert "too large" in str(exc_info.value).lower()
    assert exc_info.value.suggestions


def test_layout_with_repair_blocks_unplaced_pieces(monkeypatch: pytest.MonkeyPatch) -> None:
    piece = _oversize_piece(50, 50, label="Ghost")

    def fake_layout_pieces(
        pieces: list[UnfoldPiece],
        paper_size: PaperSize,
        *,
        gap_mm: float = 8.0,
        cancel_check=None,
    ) -> LayoutPlacementResult:
        return LayoutPlacementResult(pages=[], unplaced_pieces=list(pieces))

    monkeypatch.setattr("app.services.layout_repair.layout_pieces", fake_layout_pieces)

    result = layout_with_repair([piece], PaperSize.A4)
    assert result.export_blocked is True
    assert "Ghost" in result.messages[0]

    with pytest.raises(LayoutFitError):
        ensure_layout_exportable(result)


def test_rotated_fit_uses_same_rotation_dims() -> None:
    """Wide-short and tall-narrow bbox must not false-negative fit checks."""
    page_w, page_h = PAPER_SIZES_MM[PaperSize.A4]
    usable_w = page_w - 2 * MARGIN_MM
    usable_h = page_h - 2 * MARGIN_MM
    # 250×50 mm — fits when rotated to 50×250 if printable height allows
    piece = _oversize_piece(250, 50, label="Strip")
    oversize = find_pieces_too_large_for_paper([piece], PaperSize.A4)
    if usable_h >= 250:
        assert oversize == []
    else:
        assert len(oversize) == 1
