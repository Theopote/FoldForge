"""Unfold overlap strict vs warning policy."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import trimesh

from app.models.geometry import Point2D, UnfoldPiece
from app.schemas.model import Difficulty
from app.services.pipeline_errors import UnfoldRepairError
from app.services.seam_generator import compute_edge_dihedral_angles
from app.services.unfold_repair import unfold_with_auto_repair


def _box_mesh() -> trimesh.Trimesh:
    return trimesh.creation.box(extents=(40, 30, 20))


def _overlapping_piece() -> UnfoldPiece:
    return UnfoldPiece(
        id="overlap-piece",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10)],
        has_overlap=True,
    )


@pytest.fixture
def mesh_with_stubbed_overlap():
    """Box mesh whose unfold step always reports unresolved overlap."""
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    overlapping = [_overlapping_piece()]

    with (
        patch("app.services.unfold_repair.unfold_mesh", return_value=overlapping),
        patch("app.services.unfold_repair.split_into_patches", return_value=[[0]]),
        patch(
            "app.services.unfold_repair.find_best_split_seam_in_patch",
            return_value=None,
        ),
    ):
        yield mesh, data


def test_strict_mode_raises_on_unresolved_overlap(mesh_with_stubbed_overlap) -> None:
    mesh, data = mesh_with_stubbed_overlap

    with pytest.raises(UnfoldRepairError):
        unfold_with_auto_repair(
            mesh,
            Difficulty.STANDARD,
            dihedral=data,
            block_export_on_failure=True,
        )


def test_warning_mode_allows_export_with_overlap_flag(mesh_with_stubbed_overlap) -> None:
    mesh, data = mesh_with_stubbed_overlap

    result = unfold_with_auto_repair(
        mesh,
        Difficulty.STANDARD,
        dihedral=data,
        block_export_on_failure=False,
    )

    assert result.export_blocked is False
    assert result.has_unfold_overlap is True
