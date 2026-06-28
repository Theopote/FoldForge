"""Cooperative cancellation during long-running pipeline stages."""

from __future__ import annotations

import pytest

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import PaperSize
from app.services.layout_engine import layout_pieces
from app.services.layout_repair import layout_with_repair
from app.services.pipeline_errors import JobCancelledError
from app.services.unfold_repair import unfold_with_auto_repair


def _small_piece(label: str = "A") -> UnfoldPiece:
    return UnfoldPiece(
        id=f"piece-{label}",
        face_ids=[0],
        label=label,
        polygon=[
            Point2D(0, 0),
            Point2D(40, 0),
            Point2D(40, 40),
            Point2D(0, 40),
        ],
    )


def test_layout_pieces_honours_cancel_check() -> None:
    cancelled = False

    def cancel_check() -> bool:
        return cancelled

    with pytest.raises(JobCancelledError):
        cancelled = True
        layout_pieces([_small_piece()], PaperSize.A4, cancel_check=cancel_check)


def test_layout_with_repair_honours_cancel_check() -> None:
    cancelled = False

    def cancel_check() -> bool:
        return cancelled

    with pytest.raises(JobCancelledError):
        cancelled = True
        layout_with_repair(
            [_small_piece(), _small_piece("B")],
            PaperSize.A4,
            cancel_check=cancel_check,
        )


def test_unfold_with_auto_repair_honours_cancel_check(monkeypatch: pytest.MonkeyPatch) -> None:
    import trimesh

    from app.models.geometry import UnfoldPiece as Piece
    from app.schemas.model import Difficulty

    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    overlapping_piece = Piece(
        id="overlap",
        face_ids=[0],
        label="overlap",
        polygon=[Point2D(0, 0), Point2D(1, 0), Point2D(1, 1), Point2D(0, 1)],
        has_overlap=True,
    )

    def fake_unfold(*args, **kwargs):
        return [overlapping_piece]

    def fake_select_seams(*args, **kwargs):
        return set()

    def fake_split(*args, **kwargs):
        return [[0]]

    monkeypatch.setattr("app.services.unfold_repair.unfold_mesh", fake_unfold)
    monkeypatch.setattr("app.services.unfold_repair.select_seams", fake_select_seams)
    monkeypatch.setattr("app.services.unfold_repair.split_into_patches", fake_split)
    monkeypatch.setattr(
        "app.services.unfold_repair.find_best_split_seam_in_patch",
        lambda *args, **kwargs: None,
    )

    cancelled = False

    def cancel_check() -> bool:
        return cancelled

    with pytest.raises(JobCancelledError):
        cancelled = True
        unfold_with_auto_repair(mesh, Difficulty.STANDARD, cancel_check=cancel_check)
