"""Unit tests for unfolder LSCM/BFS fallback and overlap edge cases."""

from __future__ import annotations

import numpy as np
import pytest
import trimesh
from shapely.geometry import Polygon

from app.models.geometry import Point2D
from app.services.seam_generator import compute_edge_dihedral_angles
from app.services import unfolder


def _flat_quad_mesh() -> trimesh.Trimesh:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [2.0, 2.0, 0.0],
            [0.0, 2.0, 0.0],
        ],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def _degenerate_collinear_mesh() -> trimesh.Trimesh:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2]], dtype=np.int64)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def _open_book_mesh() -> trimesh.Trimesh:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def test_face_polygon_2d_rejects_collinear_vertices() -> None:
    mesh = _degenerate_collinear_mesh()
    vertex_2d = {
        0: Point2D(0.0, 0.0),
        1: Point2D(1.0, 0.0),
        2: Point2D(2.0, 0.0),
    }

    assert unfolder._face_polygon_2d(mesh, 0, vertex_2d) is None


def test_face_polygon_2d_rejects_missing_vertices() -> None:
    mesh = _flat_quad_mesh()
    vertex_2d = {0: Point2D(0.0, 0.0), 1: Point2D(2.0, 0.0)}

    assert unfolder._face_polygon_2d(mesh, 0, vertex_2d) is None


def test_face_polygon_2d_accepts_valid_triangle() -> None:
    mesh = _flat_quad_mesh()
    vertex_2d = {
        0: Point2D(0.0, 0.0),
        1: Point2D(2.0, 0.0),
        2: Point2D(2.0, 2.0),
    }

    poly = unfolder._face_polygon_2d(mesh, 0, vertex_2d)

    assert poly is not None
    assert poly.is_valid
    assert poly.area == pytest.approx(2.0)


def test_detect_face_overlap_ignores_edge_adjacent_triangles() -> None:
    left = Polygon([(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)])
    right = Polygon([(0.0, 0.0), (2.0, 2.0), (0.0, 2.0)])

    assert left.touches(right)
    assert left.intersection(right).area == pytest.approx(0.0)
    assert unfolder._detect_face_overlap(left, [right]) is False


def test_detect_face_overlap_respects_area_threshold() -> None:
    base = Polygon([(0.0, 0.0), (3.0, 0.0), (0.0, 3.0)])
    at_threshold = Polygon([(1.0, 1.0), (4.0, 1.0), (1.0, 4.0)])
    above_threshold = Polygon([(0.5, 1.0), (3.5, 1.0), (0.5, 4.0)])

    assert base.intersection(at_threshold).area == pytest.approx(
        unfolder.OVERLAP_AREA_THRESHOLD_MM2
    )
    assert unfolder._detect_face_overlap(base, [at_threshold]) is False
    assert base.intersection(above_threshold).area > unfolder.OVERLAP_AREA_THRESHOLD_MM2
    assert unfolder._detect_face_overlap(base, [above_threshold]) is True


def test_rotate_point_to_edge_handles_zero_length_edge() -> None:
    point = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    anchor = np.array([0.0, 0.0, 0.0], dtype=np.float64)

    result = unfolder._rotate_point_to_edge(
        point,
        anchor,
        anchor,
        Point2D(5.0, 6.0),
        Point2D(5.0, 6.0),
    )

    assert result.x == pytest.approx(5.0)
    assert result.y == pytest.approx(6.0)


def test_face_local_basis_handles_degenerate_collinear_face() -> None:
    mesh = _degenerate_collinear_mesh()

    origin, axis_u, axis_w = unfolder._face_local_basis(mesh, 0)

    assert np.linalg.norm(axis_u) == pytest.approx(1.0)
    assert np.linalg.norm(axis_w) == pytest.approx(0.0)
    assert origin.tolist() == pytest.approx([0.0, 0.0, 0.0])


def test_unfold_patch_lscm_flat_quad() -> None:
    mesh = _flat_quad_mesh()

    vertex_2d = unfolder._unfold_patch_lscm(mesh, [0, 1])

    assert vertex_2d is not None
    assert set(vertex_2d) == {0, 1, 2, 3}
    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], vertex_2d) is False


def test_unfold_patch_lscm_returns_none_without_faces() -> None:
    mesh = _flat_quad_mesh()

    assert unfolder._unfold_patch_lscm(mesh, []) is None


def test_unfold_patch_bfs_flat_patch_no_overlap() -> None:
    mesh = _flat_quad_mesh()
    dihedral = compute_edge_dihedral_angles(mesh)

    vertex_2d, overlap_detected = unfolder._unfold_patch_bfs(mesh, [0, 1], dihedral)

    assert overlap_detected is False
    assert set(vertex_2d) == {0, 1, 2, 3}
    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], vertex_2d) is False


def test_unfold_patch_bfs_open_book_patch() -> None:
    mesh = _open_book_mesh()
    dihedral = compute_edge_dihedral_angles(mesh)

    vertex_2d, overlap_detected = unfolder._unfold_patch_bfs(mesh, [0, 1], dihedral)

    assert overlap_detected is False
    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], vertex_2d) is False


def test_bfs_tries_flipped_orientation_when_default_overlaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh = _flat_quad_mesh()
    dihedral = compute_edge_dihedral_angles(mesh)
    original_detect = unfolder._detect_face_overlap
    calls = {"count": 0}

    def forced_first_overlap(new_face: Polygon, placed: list[Polygon]) -> bool:
        calls["count"] += 1
        if calls["count"] == 1:
            return True
        return original_detect(new_face, placed)

    monkeypatch.setattr(unfolder, "_detect_face_overlap", forced_first_overlap)

    vertex_2d, overlap_detected = unfolder._unfold_patch_bfs(mesh, [0, 1], dihedral)

    assert calls["count"] >= 2
    assert overlap_detected is False
    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], vertex_2d) is False


def test_bfs_sets_overlap_flag_when_both_orientations_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh = _flat_quad_mesh()
    dihedral = compute_edge_dihedral_angles(mesh)

    monkeypatch.setattr(
        unfolder,
        "_detect_face_overlap",
        lambda _new_face, placed: bool(placed),
    )

    _vertex_2d, overlap_detected = unfolder._unfold_patch_bfs(mesh, [0, 1], dihedral)

    assert overlap_detected is True


def test_vertex_map_has_overlap_detects_crossing_triangles() -> None:
    mesh = _flat_quad_mesh()
    crossed = {
        0: Point2D(0.0, 0.0),
        1: Point2D(3.0, 0.0),
        2: Point2D(0.0, 3.0),
        3: Point2D(2.0, 1.0),
    }

    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], crossed) is True
    pairs = unfolder.find_overlapping_face_pairs(mesh, [0, 1], crossed)
    assert pairs
    assert pairs[0][2] > unfolder.OVERLAP_AREA_THRESHOLD_MM2


def test_compute_unfold_vertex_map_falls_back_when_lscm_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh = _flat_quad_mesh()
    dihedral = compute_edge_dihedral_angles(mesh)
    bfs_called = {"value": False}
    original_bfs = unfolder._unfold_patch_bfs

    def tracking_bfs(*args, **kwargs):
        bfs_called["value"] = True
        return original_bfs(*args, **kwargs)

    monkeypatch.setattr(unfolder, "_unfold_patch_lscm", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(unfolder, "_unfold_patch_bfs", tracking_bfs)

    vertex_2d, has_overlap = unfolder.compute_unfold_vertex_map(mesh, [0, 1], dihedral)

    assert bfs_called["value"] is True
    assert set(vertex_2d) == {0, 1, 2, 3}
    assert has_overlap is False


def test_compute_unfold_vertex_map_falls_back_when_lscm_overlaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh = _flat_quad_mesh()
    dihedral = compute_edge_dihedral_angles(mesh)
    overlapping_lscm = {
        0: Point2D(0.0, 0.0),
        1: Point2D(3.0, 0.0),
        2: Point2D(0.0, 3.0),
        3: Point2D(2.0, 1.0),
    }
    bfs_called = {"value": False}
    original_bfs = unfolder._unfold_patch_bfs

    def tracking_bfs(*args, **kwargs):
        bfs_called["value"] = True
        return original_bfs(*args, **kwargs)

    monkeypatch.setattr(unfolder, "_unfold_patch_lscm", lambda *_args, **_kwargs: overlapping_lscm)
    monkeypatch.setattr(unfolder, "_unfold_patch_bfs", tracking_bfs)

    vertex_2d, has_overlap = unfolder.compute_unfold_vertex_map(mesh, [0, 1], dihedral)

    assert bfs_called["value"] is True
    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], overlapping_lscm) is True
    assert unfolder._vertex_map_has_overlap(mesh, [0, 1], vertex_2d) is False
    assert has_overlap is False
