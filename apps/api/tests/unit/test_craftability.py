"""Craftability scoring tests."""

from __future__ import annotations

import trimesh

from app.models.geometry import LayoutPage, PlacedPiece, Point2D, Tab, UnfoldPiece
from app.schemas.model import Difficulty
from app.services.craftability_scorer import (
    MIN_PIECE_DIMENSION_MM,
    MIN_TAB_WIDTH_MM,
    compute_craftability,
)


def _sample_piece(
    *,
    label: str = "A",
    width: float = 40.0,
    height: float = 30.0,
    has_overlap: bool = False,
    tabs: list[Tab] | None = None,
) -> UnfoldPiece:
    polygon = [
        Point2D(0, 0),
        Point2D(width, 0),
        Point2D(width, height),
        Point2D(0, height),
    ]
    return UnfoldPiece(
        id=f"piece-{label}",
        face_ids=[0],
        polygon=polygon,
        tabs=tabs or [],
        fold_lines=[],
        cut_lines=[],
        label=label,
        has_overlap=has_overlap,
    )


def _sample_page(piece: UnfoldPiece) -> LayoutPage:
    return LayoutPage(
        index=0,
        width_mm=210.0,
        height_mm=297.0,
        placed_pieces=[PlacedPiece(piece=piece, offset_x=10, offset_y=10, page_index=0)],
    )


def test_craftability_returns_score_level_and_warnings() -> None:
    mesh = trimesh.creation.box(extents=(40, 40, 40))
    piece = _sample_piece()
    score, level, warnings = compute_craftability(
        mesh,
        [piece],
        [_sample_page(piece)],
        Difficulty.STANDARD,
        [],
    )

    assert 0 <= score <= 100
    assert level in {"excellent", "good", "fair", "poor"}
    assert isinstance(warnings, list)


def test_craftability_warns_on_small_piece() -> None:
    mesh = trimesh.creation.box(extents=(20, 20, 20))
    piece = _sample_piece(width=8.0, height=20.0)
    _, _, warnings = compute_craftability(
        mesh,
        [piece],
        [_sample_page(piece)],
        Difficulty.STANDARD,
        [],
    )

    assert any(str(MIN_PIECE_DIMENSION_MM)[:2] in warning for warning in warnings)


def test_craftability_warns_on_small_tab() -> None:
    mesh = trimesh.creation.box(extents=(40, 40, 40))
    tiny_tab = Tab(
        id="tab-1",
        edge_id="edge-1",
        polygon=[
            Point2D(0, 0),
            Point2D(3, 0),
            Point2D(3, 8),
            Point2D(0, 8),
        ],
        target_piece_id="piece-B",
        label="a",
    )
    piece = _sample_piece(tabs=[tiny_tab])
    _, _, warnings = compute_craftability(
        mesh,
        [piece],
        [_sample_page(piece)],
        Difficulty.STANDARD,
        [],
    )

    assert any("glue tab" in warning.lower() for warning in warnings)
    assert any(str(int(MIN_TAB_WIDTH_MM)) in warning for warning in warnings)


def test_craftability_warns_on_piece_overlap() -> None:
    mesh = trimesh.creation.box(extents=(40, 40, 40))
    piece = _sample_piece(has_overlap=True)
    score, _, warnings = compute_craftability(
        mesh,
        [piece],
        [_sample_page(piece)],
        Difficulty.STANDARD,
        [],
    )

    assert score < 100
    assert any("overlap" in warning.lower() for warning in warnings)


def test_craftability_warns_on_many_pages() -> None:
    mesh = trimesh.creation.box(extents=(40, 40, 40))
    piece = _sample_piece()
    pages = [
        LayoutPage(index=i, width_mm=210, height_mm=297, placed_pieces=[])
        for i in range(7)
    ]
    _, _, warnings = compute_craftability(
        mesh,
        [piece],
        pages,
        Difficulty.STANDARD,
        [],
        layout_has_overlaps=False,
    )

    assert any("7 pages" in warning for warning in warnings)
