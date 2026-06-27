"""Seam selection — split mesh into unfoldable patches."""

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


def _edge_key(v0: int, v1: int) -> tuple[int, int]:
    return (v0, v1) if v0 < v1 else (v1, v0)


def compute_edge_dihedral_angles(mesh: trimesh.Trimesh) -> dict[tuple[int, int], float]:
    """Map each interior edge to its dihedral angle in radians."""
    angles: dict[tuple[int, int], float] = {}

    for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
        f1, f2 = int(face_pair[0]), int(face_pair[1])
        v0, v1 = int(edge_verts[0]), int(edge_verts[1])
        key = _edge_key(v0, v1)

        n1 = mesh.face_normals[f1]
        n2 = mesh.face_normals[f2]
        dot = float(np.clip(np.dot(n1, n2), -1.0, 1.0))
        angles[key] = float(np.arccos(dot))

    return angles


def select_seams(mesh: trimesh.Trimesh, difficulty: Difficulty) -> set[tuple[int, int]]:
    """
    Select seam edges based on dihedral angle and patch size limits.

    Returns a set of vertex-pair keys representing cut edges.
    """
    dihedral = compute_edge_dihedral_angles(mesh)
    threshold = SEAM_ANGLE_THRESHOLD[difficulty]
    max_faces = MAX_FACES_PER_PATCH[difficulty]

    seams: set[tuple[int, int]] = {
        edge for edge, angle in dihedral.items() if angle >= threshold
    }

    # Force additional seams until all patches are within size limit
    for _ in range(len(mesh.faces)):
        patches = split_into_patches(mesh, seams)
        oversized = [p for p in patches if len(p) > max_faces]
        if not oversized:
            break

        added = False
        for patch in oversized:
            patch_set = set(patch)
            best_edge: tuple[int, int] | None = None
            best_angle = -1.0

            for face_pair, edge_verts in zip(mesh.face_adjacency, mesh.face_adjacency_edges):
                f1, f2 = int(face_pair[0]), int(face_pair[1])
                if f1 not in patch_set or f2 not in patch_set:
                    continue

                key = _edge_key(int(edge_verts[0]), int(edge_verts[1]))
                if key in seams:
                    continue

                angle = dihedral.get(key, 0.0)
                if angle > best_angle:
                    best_angle = angle
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
