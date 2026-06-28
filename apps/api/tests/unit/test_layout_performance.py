"""Layout performance — shelf fallback for large piece counts."""

from __future__ import annotations

import time

import pytest

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.layout_engine import (
    layout_has_complete_placement,
    layout_pieces,
    layout_pieces_nfp,
    layout_pieces_shelf,
)
from app.services.nfp_packing import nfp_placement_candidates
from shapely.geometry import box


def _square(size: float, label: str) -> UnfoldPiece:
    return UnfoldPiece(
        id=f"piece-{label}",
        face_ids=[0],
        label=label,
        polygon=[
            Point2D(0, 0),
            Point2D(size, 0),
            Point2D(size, size),
            Point2D(0, size),
        ],
    )


def test_nfp_candidates_skipped_when_stationary_cap_exceeded() -> None:
    stationary = [box(0, 0, 10, 10) for _ in range(15)]
    orbiting = box(0, 0, 8, 8)

    assert nfp_placement_candidates(stationary, orbiting, max_stationary=12) == []


def test_layout_many_pieces_uses_shelf_path(monkeypatch: pytest.MonkeyPatch) -> None:
    shelf_called = {"value": False}
    nfp_called = {"value": False}

    def track_shelf(*args, **kwargs):
        shelf_called["value"] = True
        return layout_pieces_shelf(*args, **kwargs)

    def track_nfp(*args, **kwargs):
        nfp_called["value"] = True
        return layout_pieces_nfp(*args, **kwargs)

    monkeypatch.setattr("app.services.layout_engine.layout_pieces_shelf", track_shelf)
    monkeypatch.setattr("app.services.layout_engine.layout_pieces_nfp", track_nfp)

    pieces = [_square(12, f"P{i:02d}") for i in range(30)]
    result = layout_pieces(pieces, PaperSize.A4)

    assert shelf_called["value"] is True
    assert nfp_called["value"] is False
    assert layout_has_complete_placement(pieces, result.pages)


def test_layout_many_pieces_completes_within_time_budget() -> None:
    pieces = [_square(10, f"P{i:02d}") for i in range(40)]

    started = time.monotonic()
    result = layout_pieces(pieces, PaperSize.A4)
    elapsed = time.monotonic() - started

    assert elapsed < 15.0
    assert layout_has_complete_placement(pieces, result.pages)
    assert result.issues.has_overlaps is False


def test_layout_small_piece_count_uses_nfp_path(monkeypatch: pytest.MonkeyPatch) -> None:
    shelf_called = {"value": False}
    nfp_called = {"value": False}

    def track_shelf(*args, **kwargs):
        shelf_called["value"] = True
        return layout_pieces_shelf(*args, **kwargs)

    def track_nfp(*args, **kwargs):
        nfp_called["value"] = True
        return layout_pieces_nfp(*args, **kwargs)

    monkeypatch.setattr("app.services.layout_engine.layout_pieces_shelf", track_shelf)
    monkeypatch.setattr("app.services.layout_engine.layout_pieces_nfp", track_nfp)

    pieces = [_square(20, "A"), _square(18, "B"), _square(16, "C")]
    layout_pieces(pieces, PaperSize.A4)

    assert nfp_called["value"] is True
    assert shelf_called["value"] is False
