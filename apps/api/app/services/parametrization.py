"""LSCM and ABF UV parameterization for mesh patch unfolding."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from app.models.geometry import Point2D

ABF_NEWTON_MAX_ITER = 30
ABF_NEWTON_TOL = 1e-6
ABF_POSITION_ITERATIONS = 12
TWO_PI = 2.0 * math.pi


def _normalize(v: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(v))
    if length < 1e-12:
        return v
    return v / length


def _face_local_coords(
    vertices: np.ndarray,
    face: np.ndarray,
) -> dict[int, tuple[float, float]]:
    """Project face vertices into the face tangent plane."""
    v0, v1, v2 = (vertices[int(face[0])], vertices[int(face[1])], vertices[int(face[2])])
    axis_u = _normalize(v1 - v0)
    normal = _normalize(np.cross(v1 - v0, v2 - v0))
    axis_w = _normalize(np.cross(normal, axis_u))
    origin = v0

    coords: dict[int, tuple[float, float]] = {}
    for vertex_idx in face:
        vi = int(vertex_idx)
        delta = vertices[vi] - origin
        coords[vi] = (float(np.dot(delta, axis_u)), float(np.dot(delta, axis_w)))
    return coords


def lscm_parameterize(
    vertices: np.ndarray,
    faces: np.ndarray,
    vertex_indices: list[int],
) -> dict[int, Point2D] | None:
    """
    Least Squares Conformal Map for a mesh patch.

    Returns UV coordinates keyed by global mesh vertex index, or None if the
    linear system is degenerate.
    """
    if len(vertex_indices) < 3:
        return None

    index_set = set(vertex_indices)
    local_faces: list[np.ndarray] = []
    for face in faces:
        if all(int(v) in index_set for v in face):
            local_faces.append(face.astype(int))

    if not local_faces:
        return None

    n_verts = len(vertices)
    n_vars = 2 * n_verts
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    row = 0

    for face in local_faces:
        local = _face_local_coords(vertices, face)
        vi, vj, vk = int(face[0]), int(face[1]), int(face[2])
        for a, b in ((vi, vj), (vj, vk), (vk, vi)):
            xa, ya = local[a]
            xb, yb = local[b]
            dx = xb - xa
            dy = yb - ya
            if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                continue

            # Conformal: (u_b - u_a) * dy - (v_b - v_a) * dx = 0
            rows.extend([row, row, row, row])
            cols.extend([2 * a, 2 * a + 1, 2 * b, 2 * b + 1])
            data.extend([-dy, dx, dy, -dx])
            row += 1

    if row < 2:
        return None

    matrix = sp.csr_matrix((data, (rows, cols)), shape=(row, n_vars))

    # Pin two vertices to remove null space: v0 at origin, farthest at (L, 0)
    pin_a = vertex_indices[0]
    pin_b = max(
        vertex_indices,
        key=lambda idx: float(np.linalg.norm(vertices[idx] - vertices[pin_a])),
    )
    if pin_b == pin_a and len(vertex_indices) > 1:
        pin_b = vertex_indices[1]

    pin_length = float(np.linalg.norm(vertices[pin_b] - vertices[pin_a]))
    if pin_length < 1e-8:
        pin_length = 1.0

    pinned_dofs = {2 * pin_a, 2 * pin_a + 1, 2 * pin_b, 2 * pin_b + 1}
    pinned_values = {
        2 * pin_a: 0.0,
        2 * pin_a + 1: 0.0,
        2 * pin_b: pin_length,
        2 * pin_b + 1: 0.0,
    }

    free_dofs = [i for i in range(n_vars) if i not in pinned_dofs]
    if not free_dofs:
        return None

    pinned_list = sorted(pinned_dofs)
    pinned_values_vec = np.array([pinned_values[i] for i in pinned_list], dtype=np.float64)
    rhs = -matrix[:, pinned_list] @ pinned_values_vec
    free_matrix = matrix[:, free_dofs]

    try:
        solution, info = spla.lsqr(free_matrix, rhs)[:2]
        if info not in (0, 1, 2):
            return None
    except Exception:
        return None

    uv = np.zeros(n_vars, dtype=np.float64)
    for dof, value in pinned_values.items():
        uv[dof] = value
    for idx, dof in enumerate(free_dofs):
        uv[dof] = solution[idx]

    return {
        vi: Point2D(float(uv[2 * vi]), float(uv[2 * vi + 1]))
        for vi in vertex_indices
    }


def abf_refine_uv(
    vertices: np.ndarray,
    faces: np.ndarray,
    vertex_indices: list[int],
    uv_map: dict[int, Point2D],
    *,
    iterations: int = 6,
) -> dict[int, Point2D]:
    """Backward-compatible wrapper — delegates to full ABF when iterations > 8."""
    if iterations > 8:
        return abf_parameterize(vertices, faces, vertex_indices, uv_map)
    return _abf_lite_refine(vertices, faces, vertex_indices, uv_map, iterations=iterations)


def abf_parameterize(
    vertices: np.ndarray,
    faces: np.ndarray,
    vertex_indices: list[int],
    uv_map: dict[int, Point2D],
) -> dict[int, Point2D]:
    """
    Sheffer-style ABF: optimize corner angles then re-embed interior vertices.

    Phase 1 — angle adjustment with 2π constraint at interior vertices.
    Phase 2 — gradient descent on vertex positions to match target angles.
    """
    index_set = set(vertex_indices)
    local_faces = [face for face in faces if all(int(v) in index_set for v in face)]
    if not local_faces:
        return uv_map

    corner_3d = _corner_angles_3d(vertices, local_faces)
    coords = {vi: np.array([uv_map[vi].x, uv_map[vi].y], dtype=np.float64) for vi in vertex_indices}
    corner_2d = _corner_angles_2d(coords, local_faces)

    interior = _interior_vertices(local_faces, index_set)
    wedges_by_vertex = _wedges_by_vertex(local_faces, interior)

    # Phase 1 — Sheffer Newton angle solve per interior vertex
    beta = dict(corner_2d)
    for vi in interior:
        keys = wedges_by_vertex.get(vi, [])
        if len(keys) < 3:
            continue
        alphas = np.array([corner_3d[k] for k in keys], dtype=np.float64)
        betas = np.array([beta[k] for k in keys], dtype=np.float64)
        solved = _sheffer_newton_vertex_angles(alphas, betas)
        for key, value in zip(keys, solved):
            beta[key] = float(value)

    # Phase 2 — move interior vertices toward target wedge angles
    for _ in range(ABF_POSITION_ITERATIONS):
        for vi in interior:
            keys = wedges_by_vertex.get(vi, [])
            if len(keys) < 3:
                continue
            gradient = _angle_mismatch_gradient(coords, keys, beta)
            coords[vi] = coords[vi] - 0.35 * gradient

    return {vi: Point2D(float(coords[vi][0]), float(coords[vi][1])) for vi in vertex_indices}


def _sheffer_newton_vertex_angles(
    alphas: np.ndarray,
    betas: np.ndarray,
    *,
    max_iter: int = ABF_NEWTON_MAX_ITER,
    tol: float = ABF_NEWTON_TOL,
) -> np.ndarray:
    """
    Sheffer ABF Phase-1 Newton solve for wedge angles at one interior vertex.

    Minimizes Σ ((βᵢ - αᵢ) / αᵢ)² subject to Σ βᵢ = 2π using projected Newton steps.
    """
    n = len(alphas)
    if n == 0:
        return betas
    if n == 1:
        return np.array([TWO_PI], dtype=np.float64)

    beta = np.clip(betas.astype(np.float64), 1e-4, np.pi - 1e-4)
    if float(beta.sum()) < 1e-8:
        beta = np.full(n, TWO_PI / n, dtype=np.float64)
    else:
        beta = beta / float(beta.sum()) * TWO_PI

    inv_a2 = 1.0 / np.maximum(alphas * alphas, 1e-10)

    for _ in range(max_iter):
        err = beta - alphas
        if float(np.max(np.abs(err))) < tol and abs(float(beta.sum()) - TWO_PI) < tol:
            break

        grad = inv_a2 * err
        grad -= float(grad.mean())

        hess_diag = inv_a2
        step = -grad / hess_diag
        step -= float(step.mean())

        beta = beta + 0.85 * step
        beta = np.clip(beta, 1e-4, np.pi - 1e-4)
        beta = beta / float(beta.sum()) * TWO_PI

    return beta


def _abf_lite_refine(
    vertices: np.ndarray,
    faces: np.ndarray,
    vertex_indices: list[int],
    uv_map: dict[int, Point2D],
    *,
    iterations: int = 6,
) -> dict[int, Point2D]:
    """Fast angle-sum scaling fallback."""
    index_set = set(vertex_indices)
    local_faces = [face for face in faces if all(int(v) in index_set for v in face)]
    if not local_faces:
        return uv_map

    adjacency: dict[int, set[int]] = {vi: set() for vi in vertex_indices}
    for face in local_faces:
        a, b, c = int(face[0]), int(face[1]), int(face[2])
        adjacency[a].update((b, c))
        adjacency[b].update((a, c))
        adjacency[c].update((a, b))

    coords = {vi: np.array([uv_map[vi].x, uv_map[vi].y], dtype=np.float64) for vi in vertex_indices}

    boundary = {
        vi
        for vi in vertex_indices
        if len(adjacency.get(vi, ())) > 0 and _is_boundary_vertex(vi, local_faces, index_set)
    }
    interior = [vi for vi in vertex_indices if vi not in boundary]

    for _ in range(iterations):
        for vi in interior:
            neighbors = sorted(adjacency.get(vi, ()))
            if len(neighbors) < 3:
                continue

            target = _target_angle_sum_3d(vertices, local_faces, vi)
            current = _angle_sum_2d(coords, local_faces, vi)
            if abs(current) < 1e-8:
                continue

            scale = target / current
            neighbor_pts = np.array([coords[n] for n in neighbors])
            centroid = neighbor_pts.mean(axis=0)
            direction = coords[vi] - centroid
            coords[vi] = centroid + direction * scale * 0.35

    return {vi: Point2D(float(coords[vi][0]), float(coords[vi][1])) for vi in vertex_indices}



def _corner_angles_3d(
    vertices: np.ndarray,
    local_faces: list[np.ndarray],
) -> dict[tuple[tuple[int, int, int], int], float]:
    angles: dict[tuple[tuple[int, int, int], int], float] = {}
    for face in local_faces:
        for vi in face:
            angle = _angle_at_vertex_3d(vertices, face, int(vi))
            if angle is not None:
                angles[(tuple(int(v) for v in face), int(vi))] = angle
    return angles


def _corner_angles_2d(
    coords: dict[int, np.ndarray],
    local_faces: list[np.ndarray],
) -> dict[tuple[tuple[int, int, int], int], float]:
    angles: dict[tuple[tuple[int, int, int], int], float] = {}
    for face in local_faces:
        for vi in face:
            angle = _angle_at_vertex_2d(coords, face, int(vi))
            if angle is not None:
                angles[(tuple(int(v) for v in face), int(vi))] = angle
    return angles


def _interior_vertices(
    local_faces: list[np.ndarray],
    patch_vertices: set[int],
) -> list[int]:
    return [
        vi
        for vi in patch_vertices
        if not _is_boundary_vertex(vi, local_faces, patch_vertices)
    ]


def _wedges_by_vertex(
    local_faces: list[np.ndarray],
    interior: list[int],
) -> dict[int, list[tuple[tuple[int, int, int], int]]]:
    wedges: dict[int, list[tuple[tuple[int, int, int], int]]] = defaultdict(list)
    interior_set = set(interior)
    for face in local_faces:
        face_key = tuple(int(v) for v in face)
        for vi in face:
            vi_int = int(vi)
            if vi_int in interior_set:
                wedges[vi_int].append((face_key, vi_int))
    return wedges


def _angle_mismatch_gradient(
    coords: dict[int, np.ndarray],
    wedge_keys: list[tuple[tuple[int, int, int], int]],
    target_angles: dict[tuple[tuple[int, int, int], int], float],
) -> np.ndarray:
    """Finite-difference gradient of squared angle error for one vertex."""
    if not wedge_keys:
        return np.zeros(2, dtype=np.float64)

    vi = wedge_keys[0][1]
    base = _wedge_angle_error(coords, wedge_keys, target_angles)
    gradient = np.zeros(2, dtype=np.float64)
    step = 0.25

    for axis in range(2):
        trial = {k: v.copy() for k, v in coords.items()}
        trial[vi][axis] += step
        forward = _wedge_angle_error(trial, wedge_keys, target_angles)
        gradient[axis] = (forward - base) / step

    return gradient


def _wedge_angle_error(
    coords: dict[int, np.ndarray],
    wedge_keys: list[tuple[tuple[int, int, int], int]],
    target_angles: dict[tuple[tuple[int, int, int], int], float],
) -> float:
    error = 0.0
    for face_key, vi in wedge_keys:
        face = np.array(face_key, dtype=int)
        current = _angle_at_vertex_2d(coords, face, vi)
        target = target_angles.get((face_key, vi))
        if current is None or target is None:
            continue
        diff = current - target
        error += diff * diff / max(target, 1e-6)
    return error


def _is_boundary_vertex(
    vertex: int,
    faces: list[np.ndarray],
    patch_vertices: set[int],
) -> bool:
    edge_count: dict[tuple[int, int], int] = {}
    for face in faces:
        loop = [int(v) for v in face]
        for i in range(3):
            a, b = loop[i], loop[(i + 1) % 3]
            key = (a, b) if a < b else (b, a)
            edge_count[key] = edge_count.get(key, 0) + 1

    for face in faces:
        loop = [int(v) for v in face]
        if vertex not in loop:
            continue
        for i in range(3):
            a, b = loop[i], loop[(i + 1) % 3]
            if vertex not in (a, b):
                continue
            key = (a, b) if a < b else (b, a)
            if edge_count.get(key, 0) == 1:
                return True
    return False


def _angle_at_vertex_2d(
    coords: dict[int, np.ndarray],
    face: np.ndarray,
    vertex: int,
) -> float | None:
    loop = [int(v) for v in face]
    if vertex not in loop:
        return None
    idx = loop.index(vertex)
    prev_v = loop[(idx - 1) % 3]
    next_v = loop[(idx + 1) % 3]
    a = coords[prev_v] - coords[vertex]
    b = coords[next_v] - coords[vertex]
    la = float(np.linalg.norm(a))
    lb = float(np.linalg.norm(b))
    if la < 1e-12 or lb < 1e-12:
        return None
    cos_a = float(np.clip(np.dot(a, b) / (la * lb), -1.0, 1.0))
    return math.acos(cos_a)


def _angle_at_vertex_3d(
    vertices: np.ndarray,
    face: np.ndarray,
    vertex: int,
) -> float | None:
    loop = [int(v) for v in face]
    if vertex not in loop:
        return None
    idx = loop.index(vertex)
    prev_v = loop[(idx - 1) % 3]
    next_v = loop[(idx + 1) % 3]
    a = vertices[prev_v] - vertices[vertex]
    b = vertices[next_v] - vertices[vertex]
    la = float(np.linalg.norm(a))
    lb = float(np.linalg.norm(b))
    if la < 1e-12 or lb < 1e-12:
        return None
    cos_a = float(np.clip(np.dot(a, b) / (la * lb), -1.0, 1.0))
    return math.acos(cos_a)


def _angle_sum_2d(
    coords: dict[int, np.ndarray],
    faces: list[np.ndarray],
    vertex: int,
) -> float:
    total = 0.0
    for face in faces:
        angle = _angle_at_vertex_2d(coords, face, vertex)
        if angle is not None:
            total += angle
    return total


def _target_angle_sum_3d(
    vertices: np.ndarray,
    faces: list[np.ndarray],
    vertex: int,
) -> float:
    total = 0.0
    for face in faces:
        angle = _angle_at_vertex_3d(vertices, face, vertex)
        if angle is not None:
            total += angle
    return total
