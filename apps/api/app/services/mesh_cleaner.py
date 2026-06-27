"""Mesh cleaning and validation."""

import trimesh


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Clean mesh topology: merge vertices, remove degenerate faces, fix normals.

    Returns a new mesh instance safe for downstream processing.
    """
    cleaned = mesh.copy()
    cleaned.merge_vertices()
    cleaned.update_faces(cleaned.nondegenerate_faces())
    cleaned.update_faces(cleaned.unique_faces())
    cleaned.remove_unreferenced_vertices()
    cleaned.fix_normals()

    if len(cleaned.faces) == 0:
        raise ValueError("Mesh has no valid faces after cleaning.")

    return cleaned


def mesh_quality_issues(mesh: trimesh.Trimesh) -> list[str]:
    """Detect common mesh issues for craftability warnings."""
    warnings: list[str] = []

    if not mesh.is_watertight:
        warnings.append("Model is not watertight — some folds may be inaccurate.")

    if not mesh.is_winding_consistent:
        warnings.append("Inconsistent face winding detected.")

    edge_counts: dict[tuple[int, int], int] = {}
    for face in mesh.faces:
        for i in range(3):
            v0, v1 = int(face[i]), int(face[(i + 1) % 3])
            key = (v0, v1) if v0 < v1 else (v1, v0)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    non_manifold = sum(1 for count in edge_counts.values() if count > 2)
    if non_manifold > 0:
        warnings.append(f"Found {non_manifold} non-manifold edges.")

    return warnings
