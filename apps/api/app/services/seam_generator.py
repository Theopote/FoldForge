"""Seam selection — split mesh into unfoldable patches."""

from dataclasses import dataclass

import numpy as np
import trimesh

from app.schemas.model import Difficulty

# Max faces per patch before forcing additional seams
MAX_FACES_PER_PATCH: dict[Difficulty, int] = {
    Difficulty.EASY: 24,
    Difficulty.STANDARD: 40,
    Difficulty.ADVANCED: 80,
}

# Dihedral angle thresholds (radians) for automatic seams
SEAM_ANGLE_THRESHOLD: dict[Difficulty, float] = {
    Difficulty.EASY: 0.55,  # ~32°
    Difficulty.STANDARD: 0.45,  # ~26°
    Difficulty.ADVANCED: 0.35,  # ~20°
}

# Bonus weight for placing seams in concave (hidden) creases
CONCAVE_SEAM_BONUS = 0.25

# Balance weight when splitting oversized patches (0–1)
SPLIT_BALANCE_WEIGHT = 0.35


@dataclass(frozen=True)
class EdgeDihedralData:
    """Unsigned magnitude and signed convex/concave dihedral per interior edge."""

    unsigned: dict[tuple[int, int], float]
    signed: dict[tuple[int, int], float]


def _edge_key(v0: int, v1: int) -> tuple[int, int]:
    return (v0, v1) if v0 < v1 else (v1, v0)


def compute_edge_dihedral_angles(mesh: trimesh.Trimesh) -> EdgeDihedralData:
    """
    Map each interior edge to unsigned and signed dihedral angles (radians).

    Signed angle: positive = convex ridge, negative = concave crease (relative to
    the canonical edge direction v0 → v1 where v0 < v1).
    """
    unsigned: dict[tuple[int, int], float] = {}
    signed: dict[tuple[int, int], float] = {}

    for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        f1, f2 = int(face_pair[0]), int(face_pair[1])
        v0, v1 = int(edge_verts[0]), int(edge_verts[1])
        key = _edge_key(v0, v1)

        n1 = mesh.face_normals[f1]
        n2 = mesh.face_normals[f2]
        cos_a = float(np.clip(np.dot(n1, n2), -1.0, 1.0))

        # Orient edge consistently with canonical key
        if key[0] != v0:
            v0, v1 = v1, v0

        edge_vec = mesh.vertices[v1] - mesh.vertices[v0]
        edge_len = float(np.linalg.norm(edge_vec))
        if edge_len < 1e-12:
            unsigned[key] = 0.0
            signed[key] = 0.0
            continue

        sin_a = float(np.dot(np.cross(n1, n2), edge_vec / edge_len))
        signed[key] = float(np.arctan2(sin_a, cos_a))
        unsigned[key] = abs(signed[key])

    return EdgeDihedralData(unsigned=unsigned, signed=signed)


def _seam_preference_score(
    edge: tuple[int, int],
    dihedral: EdgeDihedralData,
) -> float:
    """Higher score = better seam candidate (sharp + preferably concave/hidden)."""
    magnitude = dihedral.unsigned.get(edge, 0.0)
    signed = dihedral.signed.get(edge, 0.0)
    hidden_bonus = max(0.0, -signed) * CONCAVE_SEAM_BONUS
    return magnitude + hidden_bonus


def _subpatch_sizes(
    mesh: trimesh.Trimesh,
    patch: list[int],
    cut_edge: tuple[int, int],
) -> tuple[int, int]:
    """Return face counts on each side of cut_edge within patch."""
    patch_set = set(patch)
    parent = {face: face for face in patch}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[x]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        f1, f2 = int(face_pair[0]), int(face_pair[1])
        if f1 not in patch_set or f2 not in patch_set:
            continue
        key = _edge_key(int(edge_verts[0]), int(edge_verts[1]))
        if key == cut_edge:
            continue
        union(f1, f2)

    roots: dict[int, int] = {}
    for face in patch:
        root = find(face)
        roots[root] = roots.get(root, 0) + 1

    sizes = sorted(roots.values(), reverse=True)
    if len(sizes) >= 2:
        return sizes[0], sizes[1]
    if len(sizes) == 1:
        return sizes[0], 0
    return 0, 0


def _split_balance_score(patch_size: int, side_a: int, side_b: int) -> float:
    """1.0 when perfectly balanced, 0.0 when one side is empty."""
    if patch_size <= 0 or side_a <= 0 or side_b <= 0:
        return 0.0
    return 1.0 - abs(side_a - side_b) / patch_size


def select_seams(
    mesh: trimesh.Trimesh,
    difficulty: Difficulty,
    dihedral: EdgeDihedralData | None = None,
) -> set[tuple[int, int]]:
    """
    Select seam edges based on dihedral angle, hidden-crease preference, and patch size.

    Returns a set of vertex-pair keys representing cut edges.
    """
    data = dihedral or compute_edge_dihedral_angles(mesh)
    threshold = SEAM_ANGLE_THRESHOLD[difficulty]
    max_faces = MAX_FACES_PER_PATCH[difficulty]

    # Auto-seam at sharp creases; slightly lower threshold for concave edges
    seams: set[tuple[int, int]] = set()
    for edge, magnitude in data.unsigned.items():
        signed = data.signed.get(edge, 0.0)
        concave_threshold = threshold * 0.85
        if magnitude >= threshold or (signed < -0.05 and magnitude >= concave_threshold):
            seams.add(edge)

    # Force balanced splits until all patches are within size limit
    for _ in range(len(mesh.faces)):
        patches = split_into_patches(mesh, seams)
        oversized = [p for p in patches if len(p) > max_faces]
        if not oversized:
            break

        added = False
        for patch in oversized:
            patch_set = set(patch)
            best_edge: tuple[int, int] | None = None
            best_score = -1.0

            for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
                f1, f2 = int(face_pair[0]), int(face_pair[1])
                if f1 not in patch_set or f2 not in patch_set:
                    continue

                key = _edge_key(int(edge_verts[0]), int(edge_verts[1]))
                if key in seams:
                    continue

                preference = _seam_preference_score(key, data)
                side_a, side_b = _subpatch_sizes(mesh, patch, key)
                balance = _split_balance_score(len(patch), side_a, side_b)
                score = preference + balance * SPLIT_BALANCE_WEIGHT

                if score > best_score:
                    best_score = score
                    best_edge = key

            if best_edge is not None:
                seams.add(best_edge)
                added = True

        if not added:
            break

    return seams


def split_into_patches(
    mesh: trimesh.Trimesh,
    seams: set[tuple[int, int]],
) -> list[list[int]]:
    """Group faces into connected patches that do not cross seam edges."""
    n_faces = len(mesh.faces)
    parent = list(range(n_faces))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        f1, f2 = int(face_pair[0]), int(face_pair[1])
        key = _edge_key(int(edge_verts[0]), int(edge_verts[1]))
        if key not in seams:
            union(f1, f2)

    groups: dict[int, list[int]] = {}
    for face_idx in range(n_faces):
        root = find(face_idx)
        groups.setdefault(root, []).append(face_idx)

    return list(groups.values())
