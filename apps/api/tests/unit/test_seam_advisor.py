"""Seam advisor tests."""

from __future__ import annotations

import trimesh

from app.schemas.model import Difficulty
from app.services.seam_advisor import (
    build_face_overlap_heat,
    build_seam_advisor,
    build_seam_guidance,
)
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.seam_editor import apply_seam_toggle
from app.services.unfolder import unfold_mesh


def test_build_seam_advisor_includes_edge_hints() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    pieces = unfold_mesh(mesh, split_into_patches(mesh, seams), dihedral=dihedral)

    advisor = build_seam_advisor(mesh, pieces, seams, Difficulty.STANDARD, dihedral)
    assert isinstance(advisor["suggestions"], list)
    assert isinstance(advisor["edgeHints"], dict)
    assert isinstance(advisor["faceHeat"], dict)
    assert isinstance(advisor["guidance"], list)
    assert len(advisor["edgeHints"]) > 0
    assert len(advisor["guidance"]) >= 1


def test_apply_seam_toggle_reflected_in_edge_hints() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    edge = next(iter(dihedral.unsigned.keys()))
    if edge in seams:
        updated, error = apply_seam_toggle(mesh, seams, edge, Difficulty.STANDARD)
        assert error is None
        assert edge not in updated
    else:
        updated, error = apply_seam_toggle(mesh, seams, edge, Difficulty.STANDARD)
        assert error is None
        assert edge in updated


def test_build_seam_guidance_mentions_layout() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    pieces = unfold_mesh(mesh, split_into_patches(mesh, seams), dihedral=dihedral)
    advisor = build_seam_advisor(mesh, pieces, seams, Difficulty.STANDARD, dihedral)

    guidance = build_seam_guidance(
        pieces,
        seams,
        advisor["overlapPieces"],
        advisor["suggestions"],
        advisor["edgeHints"],
    )
    assert any("piece" in line.lower() for line in guidance)


def test_build_face_overlap_heat_normalized() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    pieces = unfold_mesh(mesh, split_into_patches(mesh, seams), dihedral=dihedral)

    heat = build_face_overlap_heat(mesh, pieces, dihedral)
    assert isinstance(heat, dict)
    for value in heat.values():
        assert 0 <= value <= 1


def test_build_seam_guidance_mentions_layout() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    pieces = unfold_mesh(mesh, split_into_patches(mesh, seams), dihedral=dihedral)
    advisor = build_seam_advisor(mesh, pieces, seams, Difficulty.STANDARD, dihedral)

    guidance = build_seam_guidance(
        pieces,
        seams,
        advisor["overlapPieces"],
        advisor["suggestions"],
        advisor["edgeHints"],
    )
    assert any("piece" in line.lower() for line in guidance)


def test_build_face_overlap_heat_normalized() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=dihedral)
    pieces = unfold_mesh(mesh, split_into_patches(mesh, seams), dihedral=dihedral)

    heat = build_face_overlap_heat(mesh, pieces, dihedral)
    assert isinstance(heat, dict)
    for value in heat.values():
        assert 0 <= value <= 1
