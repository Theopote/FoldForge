"""Quick tests for seam / unfold / layout improvements."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import trimesh

from app.schemas.model import Difficulty, PaperSize
from app.services.layout_engine import layout_pieces
from app.services.parametrization import lscm_parameterize
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.tab_generator import add_tabs_to_pieces
from app.services.unfolder import detect_unfold_overlaps, unfold_mesh


def _box_mesh() -> trimesh.Trimesh:
    return trimesh.creation.box(extents=(40, 30, 20))


def _icosahedron() -> trimesh.Trimesh:
    return trimesh.creation.icosphere(subdivisions=1, radius=25)


def test_signed_dihedral_box() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    sharp = [angle for angle in data.unsigned.values() if angle > 0.1]
    assert sharp and all(abs(angle - 1.5708) < 0.01 for angle in sharp)
    print("signed dihedral box: ok", len(data.signed), "sharp edges", len(sharp))


def test_lscm_box_face() -> None:
    mesh = _box_mesh()
    verts = sorted({int(v) for v in mesh.faces[0]})
    uv = lscm_parameterize(mesh.vertices, mesh.faces, verts)
    assert uv is not None and len(uv) == len(verts)
    print("lscm single face: ok")


def test_seam_split_limits() -> None:
    mesh = _icosahedron()
    data = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.EASY, dihedral=data)
    patches = split_into_patches(mesh, seams)
    assert all(len(p) <= 24 for p in patches)
    print("seam split easy:", len(patches), "patches")


def test_unfold_layout_tabs() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=data)
    patches = split_into_patches(mesh, seams)
    pieces = unfold_mesh(mesh, patches, dihedral=data)
    pieces = add_tabs_to_pieces(pieces, add_tabs=True, add_numbers=True)
    pages = layout_pieces(pieces, PaperSize.A4)
    warnings = detect_unfold_overlaps(pieces)

    assert len(pieces) >= 1
    assert len(pages) >= 1
    assert all(len(p.polygon) >= 3 for p in pieces)

    paired = [t for p in pieces for t in p.tabs if t.target_piece_id]
    print(
        "unfold/layout/tabs:",
        len(pieces),
        "pieces",
        len(pages),
        "pages",
        len(paired),
        "paired tabs",
        "warnings:",
        warnings,
    )


def main() -> None:
    test_signed_dihedral_box()
    test_lscm_box_face()
    test_seam_split_limits()
    test_unfold_layout_tabs()
    print("All geometry tests passed.")


if __name__ == "__main__":
    main()
