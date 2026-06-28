"""Unit tests for seam editing validation."""

from __future__ import annotations

import trimesh

from app.schemas.model import Difficulty
from app.services.seam_editor import apply_seam_toggle, validate_seam_set
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.seam_store import format_seam_list, parse_mesh_edge, save_seam_set, load_seam_set


def test_apply_seam_toggle_adds_and_removes_edge(tmp_path) -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    interior = next(iter(dihedral.unsigned.keys()))

    if interior in seams:
        updated, error = apply_seam_toggle(mesh, seams, interior, Difficulty.STANDARD)
        assert error is None
        assert interior not in updated
        updated2, error2 = apply_seam_toggle(mesh, updated, interior, Difficulty.STANDARD)
        assert error2 is None
        assert interior in updated2
    else:
        updated, error = apply_seam_toggle(mesh, seams, interior, Difficulty.STANDARD)
        assert error is None
        assert interior in updated


def test_validate_seam_set_rejects_unknown_edge() -> None:
    mesh = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    error = validate_seam_set(mesh, {(999, 1000)}, Difficulty.EASY)
    assert error is not None
    assert "interior mesh edge" in error


def test_seam_store_roundtrip(tmp_path, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "cache_dir", tmp_path)
    seams = {(0, 1), (2, 3)}
    save_seam_set("demo", seams)
    loaded = load_seam_set("demo")
    assert loaded == seams
    assert format_seam_list(seams) == ["0,1", "2,3"]
    assert parse_mesh_edge("3,2") == (2, 3)
