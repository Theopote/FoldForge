"""Layout geometry edge cases — no silent piece loss, actionable failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import Difficulty, PaperSize, ProjectSettings, Style
from app.services.layout_engine import find_pieces_too_large_for_paper, layout_pieces
from app.services.layout_repair import ensure_layout_exportable, layout_with_repair
from app.services.papercraft_pipeline import run_pipeline
from app.services.pipeline_errors import LayoutFitError
from app.services.unfolder import piece_bounds, piece_to_shapely


def _square(width: float, height: float, label: str = "A") -> UnfoldPiece:
    return UnfoldPiece(
        id=f"piece-{label}",
        face_ids=[0],
        label=label,
        polygon=[
            Point2D(0, 0),
            Point2D(width, 0),
            Point2D(width, height),
            Point2D(0, height),
        ],
    )


def _bowtie_outline() -> list[Point2D]:
    return [
        Point2D(0, 0),
        Point2D(40, 40),
        Point2D(40, 0),
        Point2D(0, 40),
    ]


def _invalid_cut_outline_piece(label: str = "BadCut") -> UnfoldPiece:
    """BBox fits paper, but Shapely geometry is empty (self-intersecting cut outline)."""
    return UnfoldPiece(
        id=f"piece-{label}",
        face_ids=[0],
        label=label,
        polygon=[],
        cut_outline=_bowtie_outline(),
    )


def _bowtie_polygon_piece(label: str = "Bowtie") -> UnfoldPiece:
    """Self-intersecting polygon: bbox precheck passes, placement cannot succeed."""
    return UnfoldPiece(
        id=f"piece-{label}",
        face_ids=[0],
        label=label,
        polygon=_bowtie_outline(),
    )


@pytest.mark.parametrize(
    "piece_factory",
    [_invalid_cut_outline_piece, _bowtie_polygon_piece],
)
def test_degenerate_piece_passes_precheck_but_is_unplaced(piece_factory) -> None:
    piece = piece_factory()

    assert find_pieces_too_large_for_paper([piece], PaperSize.A4) == []
    assert piece_to_shapely(piece, include_tabs=True).is_empty

    result = layout_pieces([piece], PaperSize.A4)
    placed_count = sum(len(page.placed_pieces) for page in result.pages)

    assert placed_count == 0
    assert len(result.unplaced_pieces) == 1
    assert result.unplaced_pieces[0].id == piece.id


def test_mixed_valid_and_degenerate_pieces_blocks_export() -> None:
    valid = _square(30, 30, label="OK")
    bad = _invalid_cut_outline_piece(label="BadCut")

    result = layout_pieces([valid, bad], PaperSize.A4)
    placed_ids = {
        placed.piece.id
        for page in result.pages
        for placed in page.placed_pieces
    }

    assert placed_ids == {valid.id}
    assert [piece.label for piece in result.unplaced_pieces] == ["BadCut"]

    repair = layout_with_repair([valid, bad], PaperSize.A4)
    assert repair.export_blocked is True
    assert "BadCut" in repair.messages[0]
    assert repair.suggestions

    with pytest.raises(LayoutFitError) as exc_info:
        ensure_layout_exportable(repair)

    assert "BadCut" in str(exc_info.value)
    assert exc_info.value.suggestions


def test_all_valid_pieces_are_placed_without_unplaced() -> None:
    pieces = [_square(30, 30, label="A"), _square(25, 25, label="B")]

    result = layout_pieces(pieces, PaperSize.A4)
    placed_ids = {
        placed.piece.id
        for page in result.pages
        for placed in page.placed_pieces
    }

    assert result.unplaced_pieces == []
    assert placed_ids == {piece.id for piece in pieces}


def test_run_pipeline_raises_layout_fit_error_when_layout_blocked(
    test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixtures_dir: Path,
) -> None:
    from app.services.layout_repair import LayoutRepairResult

    def blocked_layout(*_args, **_kwargs) -> LayoutRepairResult:
        return LayoutRepairResult(
            pages=[],
            messages=[
                "Could not place piece(s) Panel X on the page — layout export blocked."
            ],
            export_blocked=True,
            suggestions=[
                "Use a larger paper size (e.g. A3 instead of A4).",
                "Reduce target height so all pieces shrink uniformly.",
            ],
        )

    monkeypatch.setattr(
        "app.services.papercraft_pipeline.layout_with_repair",
        blocked_layout,
    )

    source = fixtures_dir / "cube.stl"
    if not source.exists():
        pytest.skip("Missing cube.stl fixture")

    with pytest.raises(LayoutFitError) as exc_info:
        run_pipeline(
            project_id="layout-boundary-test",
            source_path=source,
            project_name="Layout Boundary",
            settings=ProjectSettings(
                paperSize=PaperSize.A4,
                difficulty=Difficulty.EASY,
                style=Style.LOW_POLY,
                targetHeightMm=80.0,
                addTabs=False,
                addNumbers=True,
                addFoldLines=True,
                addCutLines=True,
            ),
            source_original_path=source,
        )

    assert "Panel X" in str(exc_info.value)
    assert exc_info.value.suggestions


def test_invalid_cut_outline_bbox_matches_outline_points() -> None:
    piece = _invalid_cut_outline_piece()
    min_x, min_y, max_x, max_y = piece_bounds(piece, include_tabs=True)

    assert (min_x, min_y, max_x, max_y) == (0, 0, 40, 40)
