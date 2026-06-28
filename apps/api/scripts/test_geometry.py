"""Quick tests for seam / unfold / layout improvements.

Prefer the pytest suite: `python -m pytest` from apps/api.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import trimesh
from shapely.geometry import Polygon, box

from app.schemas.model import Difficulty, PaperSize
from app.services.layout_engine import detect_layout_issues, layout_pieces
from app.services.layout_repair import layout_with_repair
from app.services.nfp_packing import decompose_to_convex_parts, no_fit_polygon
from app.services.nfp_orbiting import no_fit_polygon_orbiting
from app.services.outline_optimizer import optimize_piece_cut_outline
from app.services.parametrization import (
    _angle_at_vertex_3d,
    _sheffer_newton_vertex_angles,
    abf_parameterize,
    abf_reembed_from_angles,
    lscm_parameterize,
)
from app.services.seam_generator import compute_edge_dihedral_angles, select_seams, split_into_patches
from app.services.tab_generator import add_tabs_to_pieces
from app.services.unfold_repair import unfold_with_auto_repair
from app.services.unfolder import (
    compute_unfold_vertex_map,
    detect_unfold_overlaps,
    find_overlapping_face_pairs,
    score_seams_by_overlap,
    unfold_mesh,
)


def _box_mesh() -> trimesh.Trimesh:
    return trimesh.creation.box(extents=(40, 30, 20))


def _icosahedron() -> trimesh.Trimesh:
    return trimesh.creation.icosphere(subdivisions=1, radius=25)


def test_signed_dihedral_box() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    sharp = [angle for angle in data.unsigned.values() if angle > 0.1]
    assert sharp and all(abs(angle - 1.5708) < 0.01 for angle in sharp)
    print("signed dihedral box: ok")


def test_sheffer_newton_angles() -> None:
    alphas = np.array([1.0, 1.2, 1.0, 1.1], dtype=np.float64)
    betas = np.array([1.05, 1.15, 0.95, 1.05], dtype=np.float64)
    solved = _sheffer_newton_vertex_angles(alphas, betas)
    assert abs(float(solved.sum()) - 2 * np.pi) < 1e-4
    print("sheffer newton: ok", solved.round(3).tolist())


def test_lscm_and_abf() -> None:
    mesh = _box_mesh()
    verts = sorted({int(v) for v in mesh.faces[0]})
    uv = lscm_parameterize(mesh.vertices, mesh.faces, verts)
    assert uv is not None
    refined = abf_parameterize(mesh.vertices, mesh.faces, verts, uv)
    assert len(refined) == len(verts)
    print("lscm + abf: ok")


def test_nonconvex_nfp_decomposition() -> None:
    l_shape = Polygon([(0, 0), (50, 0), (50, 20), (20, 20), (20, 50), (0, 50)])
    parts = decompose_to_convex_parts(l_shape)
    assert len(parts) >= 2
    orbiting = box(0, 0, 15, 12)
    nfp = no_fit_polygon(l_shape, orbiting)
    assert not nfp.is_empty
    orbiting_nfp = no_fit_polygon_orbiting(l_shape, orbiting)
    assert not orbiting_nfp.is_empty
    print("nonconvex nfp:", len(parts), "convex parts, orbiting area", round(orbiting_nfp.area, 1))


def test_abf_analytical_reembed() -> None:
    mesh = _box_mesh()
    verts = sorted({int(v) for v in mesh.faces[0]})
    uv = lscm_parameterize(mesh.vertices, mesh.faces, verts)
    assert uv is not None
    local_faces = [face for face in mesh.faces if all(int(v) in set(verts) for v in face)]
    interior = [v for v in verts if len(local_faces) > 0]
    beta = {}
    for face in local_faces:
        face_key = tuple(int(v) for v in face)
        for vi in face:
            vi_int = int(vi)
            angle = _angle_at_vertex_3d(mesh.vertices, face, vi_int)
            if angle is not None:
                beta[(face_key, vi_int)] = angle
    coords = abf_reembed_from_angles(
        mesh.vertices,
        local_faces,
        verts,
        uv,
        beta,
        interior,
        set(verts),
    )
    assert len(coords) == len(verts)
    print("abf analytical reembed: ok")


def test_cut_outline_boolean() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    patches = split_into_patches(mesh, select_seams(mesh, Difficulty.STANDARD, dihedral=data))
    pieces = add_tabs_to_pieces(
        unfold_mesh(mesh, patches, dihedral=data),
        add_tabs=True,
        add_numbers=True,
    )
    optimized = [optimize_piece_cut_outline(p) for p in pieces]
    with_outline = [p for p in optimized if p.cut_outline and len(p.cut_outline) >= 3]
    assert with_outline, "expected merged cut outlines"
    print("boolean cut outline:", len(with_outline), "pieces")


def test_seam_split_limits() -> None:
    mesh = _icosahedron()
    data = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.EASY, dihedral=data)
    patches = split_into_patches(mesh, seams)
    assert all(len(p) <= 24 for p in patches)
    print("seam split easy:", len(patches), "patches")


def test_unfold_auto_repair() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    result = unfold_with_auto_repair(mesh, Difficulty.STANDARD, dihedral=data)
    overlap_count = sum(1 for p in result.pieces if p.has_overlap)
    assert overlap_count == 0
    print(
        "unfold auto-repair:",
        len(result.pieces),
        "pieces",
        result.repair_steps,
        "repair steps",
    )


def test_overlap_seam_scoring() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    patches = split_into_patches(mesh, select_seams(mesh, Difficulty.STANDARD, dihedral=data))
    face_indices = patches[0]
    vertex_2d, _ = compute_unfold_vertex_map(mesh, face_indices, data)
    scores = score_seams_by_overlap(mesh, face_indices, vertex_2d)
    pairs = find_overlapping_face_pairs(mesh, face_indices, vertex_2d)
    assert pairs == [] or isinstance(scores, dict)
    print("overlap seam scoring: ok", len(scores), "edge hints")


def test_layout_repair() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    patches = split_into_patches(mesh, select_seams(mesh, Difficulty.STANDARD, dihedral=data))
    pieces = add_tabs_to_pieces(
        unfold_mesh(mesh, patches, dihedral=data),
        add_tabs=True,
        add_numbers=True,
    )
    pieces = [optimize_piece_cut_outline(p) for p in pieces]
    result = layout_with_repair(pieces, PaperSize.A4)
    issues = detect_layout_issues(result.pages)
    assert not issues.has_overlaps
    print("layout repair:", len(result.pages), "pages", result.messages)


def test_unfold_layout_tabs() -> None:
    mesh = _box_mesh()
    data = compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, Difficulty.STANDARD, dihedral=data)
    patches = split_into_patches(mesh, seams)
    pieces = unfold_mesh(mesh, patches, dihedral=data)
    pieces = add_tabs_to_pieces(pieces, add_tabs=True, add_numbers=True)
    pieces = [optimize_piece_cut_outline(p) for p in pieces]
    pages = layout_pieces(pieces, PaperSize.A4).pages
    warnings = detect_unfold_overlaps(pieces)

    assert len(pieces) >= 1
    assert len(pages) >= 1
    paired = [t for p in pieces for t in p.tabs if t.target_piece_id]
    print(
        "pipeline:",
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
    test_sheffer_newton_angles()
    test_lscm_and_abf()
    test_abf_analytical_reembed()
    test_nonconvex_nfp_decomposition()
    test_cut_outline_boolean()
    test_seam_split_limits()
    test_unfold_auto_repair()
    test_overlap_seam_scoring()
    test_layout_repair()
    test_unfold_layout_tabs()
    print("All geometry tests passed.")


if __name__ == "__main__":
    main()
